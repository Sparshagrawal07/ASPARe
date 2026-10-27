import { randomBytes, randomUUID } from "node:crypto";
import { and, desc, eq } from "drizzle-orm";
import { z } from "zod";
import { assume, AssumeError, brokerConfigured, presignedTemplateUrl, quickCreateUrl, trustAccountId } from "./aws";
import { callEngine, EngineError, type EngineFix, type EngineScan } from "./engine";
import { getDb } from "./db";
import { auditLog, connections, scans } from "./schema";

export type Connection = typeof connections.$inferSelect;
export const MAX_CONNECTIONS = 5;
export const SCAN_COOLDOWN_MS = 15_000;

export const createSchema = z.object({
  provider: z.literal("aws"),
  accountId: z.string().regex(/^\d{12}$/, "An AWS account id is 12 digits"),
  name: z.string().trim().min(1).max(40),
  region: z.string().regex(/^[a-z]{2}-[a-z]+-\d$/).default("us-east-1"),
});

export const patchSchema = z.object({
  name: z.string().trim().min(1).max(40).optional(),
  mode: z.enum(["monitor", "autofix"]).optional(),
  allowedBuckets: z.array(z.string().regex(/^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$/)).max(100).optional(),
});

export const roleNameFor = (c: Pick<Connection, "id">, kind: "access" | "autofix") =>
  `${kind === "access" ? "ASPAReAccess" : "ASPAReFix"}-${c.id.replace(/-/g, "").slice(0, 8)}`;

export function view(c: Connection) {
  return {
    id: c.id,
    provider: c.provider,
    accountId: c.accountId,
    name: c.name,
    mode: c.mode,
    fixStatus: c.fixStatus,
    region: c.region,
    allowedBuckets: JSON.parse(c.allowedBuckets) as string[],
    status: c.status,
    lastError: c.lastError,
    createdAt: c.createdAt,
    lastVerifiedAt: c.lastVerifiedAt,
    lastScanAt: c.lastScanAt,
  };
}

export async function audit(userId: string, connectionId: string | null, action: string, detail: unknown = {}) {
  const db = await getDb();
  await db.insert(auditLog).values({ id: randomUUID(), userId, connectionId, action, detail: JSON.stringify(detail) });
}

export async function owned(userId: string, id: string): Promise<Connection | null> {
  const db = await getDb();
  const [row] = await db.select().from(connections).where(and(eq(connections.id, id), eq(connections.userId, userId)));
  return row ?? null;
}

export async function createConnection(userId: string, input: z.infer<typeof createSchema>): Promise<Connection | { error: string }> {
  const db = await getDb();
  const mine = await db.select({ id: connections.id }).from(connections).where(eq(connections.userId, userId));
  if (mine.length >= MAX_CONNECTIONS) return { error: `Early access allows ${MAX_CONNECTIONS} connections per account.` };
  const id = randomUUID();
  const row = {
    id,
    userId,
    provider: input.provider,
    accountId: input.accountId,
    name: input.name,
    roleName: `ASPAReAccess-${id.replace(/-/g, "").slice(0, 8)}`,
    externalId: randomBytes(24).toString("hex"),
    region: input.region,
  };
  await db.insert(connections).values(row);
  await audit(userId, id, "connection.created", { accountId: input.accountId });
  return (await owned(userId, id))!;
}

export async function launchStack(c: Connection, kind: "access" | "autofix") {
  if (!brokerConfigured()) throw new Error("AWS connections are not configured on this deployment yet.");
  const templateUrl = await presignedTemplateUrl(kind === "access" ? "aspare-access.yaml" : "aspare-autofix.yaml");
  const roleName = roleNameFor(c, kind);
  const stackName = kind === "access" ? "ASPARe-Access" : "ASPARe-AutoFix";
  return {
    url: quickCreateUrl({
      region: c.region,
      stackName,
      templateUrl,
      params: { ExternalId: c.externalId, RoleName: roleName, TrustAccountId: trustAccountId() },
    }),
    roleName,
    stackName,
  };
}

export async function verify(c: Connection, kind: "access" | "autofix"): Promise<{ ok: boolean; error?: string }> {
  const db = await getDb();
  try {
    await assume({ accountId: c.accountId, roleName: roleNameFor(c, kind), externalId: c.externalId, sessionTag: c.id.slice(0, 8) });
  } catch (err) {
    if (kind === "access") await db.update(connections).set({ lastError: (err as Error).message }).where(eq(connections.id, c.id));
    return { ok: false, error: err instanceof AssumeError ? err.message : "Verification failed" };
  }
  const patch = kind === "access" ? { status: "connected", lastError: null, lastVerifiedAt: new Date() } : { fixStatus: "connected" };
  await db.update(connections).set(patch).where(eq(connections.id, c.id));
  await audit(c.userId, c.id, kind === "access" ? "connection.verified" : "autofix.enabled");
  return { ok: true };
}

export async function runScan(c: Connection, origin: string, trigger: "manual" | "cron") {
  const db = await getDb();
  const creds = await assume({ accountId: c.accountId, roleName: roleNameFor(c, "access"), externalId: c.externalId, sessionTag: c.id.slice(0, 8) });
  const result = await callEngine<EngineScan>(origin, {
    action: "scan",
    credentials: creds,
    region: c.region,
    allowedBuckets: JSON.parse(c.allowedBuckets),
  });
  const id = randomUUID();
  await db.insert(scans).values({ id, connectionId: c.id, trigger, summary: JSON.stringify(result.summary), result: JSON.stringify(result) });
  await db.update(connections).set({ lastScanAt: new Date(), status: "connected", lastError: null }).where(eq(connections.id, c.id));
  const old = await db.select({ id: scans.id }).from(scans).where(eq(scans.connectionId, c.id)).orderBy(desc(scans.createdAt)).offset(5);
  for (const o of old) await db.delete(scans).where(eq(scans.id, o.id));
  await audit(c.userId, c.id, "scan.completed", { trigger, ...result.summary });
  return { id, result };
}

export async function latestScan(connectionId: string) {
  const db = await getDb();
  const [row] = await db.select().from(scans).where(eq(scans.connectionId, connectionId)).orderBy(desc(scans.createdAt)).limit(1);
  return row ? { id: row.id, createdAt: row.createdAt, trigger: row.trigger, result: JSON.parse(row.result) as EngineScan } : null;
}

export async function runFix(c: Connection, findingIds: string[], origin: string) {
  if (c.fixStatus !== "connected") throw new EngineError("Enable fix access for this account first.");
  const last = await latestScan(c.id);
  if (!last) throw new EngineError("Scan first, then choose what to fix.");
  const byId = new Map(last.result.findings.map((f) => [f.id, f]));
  const picked = findingIds.map((id) => byId.get(id)).filter((f): f is NonNullable<typeof f> => Boolean(f));
  const refused = picked.filter((f) => !f.autofixAllowed).map((f) => f.id);
  const ok = picked.filter((f) => f.autofixAllowed);
  if (ok.length === 0) throw new EngineError("None of the selected findings are on buckets opted in for fixes (tag aspare-autofix=true).");
  const creds = await assume({ accountId: c.accountId, roleName: roleNameFor(c, "autofix"), externalId: c.externalId, sessionTag: c.id.slice(0, 8) });
  const out = await callEngine<EngineFix>(origin, {
    action: "remediate",
    credentials: creds,
    region: c.region,
    allowedBuckets: JSON.parse(c.allowedBuckets),
    findingIds: ok.map((f) => f.id),
    buckets: [...new Set(ok.map((f) => f.resource))],
  });
  await audit(c.userId, c.id, "fix.applied", { requested: findingIds.length, applied: out.outcomes.length, refused: refused.length });
  const rescan = await runScan(c, origin, "manual");
  return { outcomes: out.outcomes, refused, scan: rescan };
}
