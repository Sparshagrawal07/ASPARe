import { eq } from "drizzle-orm";
import { runFix, runScan } from "@/server/connections";
import { getDb } from "@/server/db";
import { fail, json, originOf } from "@/server/http";
import { connections } from "@/server/schema";

export const maxDuration = 300;

/** Daily monitoring (Vercel Cron, free tier). Fixes only run for connections that opted in to automatic fixes. */
export async function GET(request: Request) {
  const secret = process.env.CRON_SECRET;
  if (!secret || request.headers.get("authorization") !== `Bearer ${secret}`) return fail("Unauthorized", 401);
  const db = await getDb();
  const rows = await db.select().from(connections).where(eq(connections.status, "connected"));
  const report: Array<{ id: string; ok: boolean; findings?: number; fixed?: number }> = [];
  for (const c of rows.slice(0, 25)) {
    try {
      const { result } = await runScan(c, originOf(request), "cron");
      let fixed = 0;
      if (c.mode === "autofix" && c.fixStatus === "connected") {
        const ids = result.findings.filter((f) => f.decision === "AUTO_REMEDIATE" && f.autofixAllowed).map((f) => f.id).slice(0, 50);
        if (ids.length) fixed = (await runFix(c, ids, originOf(request))).outcomes.length;
      }
      report.push({ id: c.id, ok: true, findings: Array.isArray(result.findings) ? result.findings.length : 0, fixed });
    } catch (err) {
      console.error("cron scan failed", c.id, (err as Error).message);
      report.push({ id: c.id, ok: false });
    }
  }
  return json({ scanned: report.length, report });
}
