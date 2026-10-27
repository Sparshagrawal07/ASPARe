import { eq } from "drizzle-orm";
import { audit, latestScan, owned, patchSchema, view } from "@/server/connections";
import { getDb } from "@/server/db";
import { fail, json, requireUser } from "@/server/http";
import { connections } from "@/server/schema";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  return json({ connection: view(conn), scan: await latestScan(conn.id) });
}

export async function PATCH(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  const parsed = patchSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return fail(parsed.error.issues[0]?.message ?? "Invalid request");
  const p = parsed.data;
  if (p.mode === "autofix" && conn.fixStatus !== "connected") return fail("Enable fix access first, then turn on automatic fixes.", 409);
  const db = await getDb();
  await db
    .update(connections)
    .set({
      ...(p.name ? { name: p.name } : {}),
      ...(p.mode ? { mode: p.mode } : {}),
      ...(p.allowedBuckets ? { allowedBuckets: JSON.stringify(p.allowedBuckets) } : {}),
    })
    .where(eq(connections.id, conn.id));
  await audit(user.id, conn.id, "connection.updated", p);
  return json({ connection: view((await owned(user.id, conn.id))!) });
}

export async function DELETE(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  const db = await getDb();
  await db.delete(connections).where(eq(connections.id, conn.id));
  await audit(user.id, null, "connection.deleted", { accountId: conn.accountId });
  return json({ ok: true });
}
