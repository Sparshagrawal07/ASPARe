import type { Finding, Incident } from "./api";

export type Connection = {
  id: string;
  provider: "aws";
  accountId: string;
  name: string;
  mode: "monitor" | "autofix";
  fixStatus: "off" | "connected";
  region: string;
  allowedBuckets: string[];
  status: "pending" | "connected" | "error";
  lastError: string | null;
  createdAt: string;
  lastVerifiedAt: string | null;
  lastScanAt: string | null;
  lastSummary?: ScanSummary | null;
};

export type ScanSummary = { buckets: number; unreadable: number; truncated: boolean; total: number; auto: number; held: number; escalations: number };
export type InventoryItem = { name: string; tags: Record<string, string>; readable: boolean; findings: number; autofixOptIn: boolean };
export type AccountFinding = Finding & { autofixAllowed: boolean };
export type AccountScan = {
  id: string;
  createdAt: string;
  trigger: string;
  result: { findings: AccountFinding[]; inventory: InventoryItem[]; incidents: Incident[]; summary: ScanSummary };
};
export type FixOutcome = {
  findingId: string;
  resource: string;
  rule: string;
  action: string;
  status: string;
  verified: boolean;
  message: string;
  before: string[];
  after: string[];
};

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({ error: "Unreadable response from the server." }));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data as T;
}

export const appApi = {
  list: () => call<{ connections: Connection[] }>("GET", "/api/connections"),
  create: (b: { provider: "aws"; accountId: string; name: string; region: string }) => call<{ connection: Connection }>("POST", "/api/connections", b),
  get: (id: string) => call<{ connection: Connection; scan: AccountScan | null }>("GET", `/api/connections/${id}`),
  patch: (id: string, b: Partial<Pick<Connection, "name" | "mode" | "allowedBuckets">>) => call<{ connection: Connection }>("PATCH", `/api/connections/${id}`, b),
  remove: (id: string) => call<{ ok: true }>("DELETE", `/api/connections/${id}`),
  launch: (id: string, kind: "access" | "autofix") => call<{ url: string; roleName: string; stackName: string }>("POST", `/api/connections/${id}/launch`, { kind }),
  verify: (id: string, kind: "access" | "autofix") => call<{ ok: boolean; error?: string; connection: Connection }>("POST", `/api/connections/${id}/verify`, { kind }),
  scan: (id: string) => call<{ scan: AccountScan; connection: Connection }>("POST", `/api/connections/${id}/scan`),
  fix: (id: string, findingIds: string[]) => call<{ outcomes: FixOutcome[]; refused: string[]; scan: AccountScan; connection: Connection }>("POST", `/api/connections/${id}/fix`, { findingIds }),
  waitlist: (provider: "azure" | "gcp") => call<{ ok: true }>("POST", "/api/waitlist", { provider }),
};

export function ago(iso: string | null): string {
  if (!iso) return "never";
  const s = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "moments ago";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}
