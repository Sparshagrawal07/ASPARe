import { createHmac } from "node:crypto";
import type { TempCredentials } from "./aws";

export class EngineError extends Error {}

/** Call the Python engine with a signed request. The engine never receives long-lived secrets. */
export async function callEngine<T>(origin: string, body: Record<string, unknown>): Promise<T> {
  const secret = process.env.ENGINE_SECRET;
  if (!secret) throw new EngineError("The engine is not configured.");
  const raw = JSON.stringify(body);
  const ts = String(Math.floor(Date.now() / 1000));
  const signature = createHmac("sha256", secret).update(`${ts}.${raw}`).digest("hex");
  const base = process.env.ENGINE_URL ?? origin;
  const res = await fetch(`${base}/api/engine`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-aspare-timestamp": ts, "x-aspare-signature": signature },
    body: raw,
    cache: "no-store",
  });
  const data = (await res.json().catch(() => ({}))) as { error?: string };
  if (!res.ok) throw new EngineError(data.error ?? `Engine error (${res.status})`);
  return data as T;
}

export type EngineScan = {
  findings: Array<{ id: string; resource: string; rule: string; decision: string | null; autofixAllowed: boolean; canFix: boolean } & Record<string, unknown>>;
  inventory: Array<{ name: string; tags: Record<string, string>; readable: boolean; findings: number; autofixOptIn: boolean }>;
  incidents: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
};

export type EngineFix = { outcomes: Array<Record<string, unknown>> };

export function credentialBlock(c: TempCredentials) {
  return { credentials: c };
}
