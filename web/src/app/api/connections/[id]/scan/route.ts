import { SCAN_COOLDOWN_MS, owned, runScan, view } from "@/server/connections";
import { AssumeError } from "@/server/aws";
import { EngineError } from "@/server/engine";
import { fail, json, originOf, requireUser } from "@/server/http";

type Ctx = { params: Promise<{ id: string }> };
export const maxDuration = 300;

export async function POST(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  if (conn.status !== "connected") return fail("Finish connecting this account first.", 409);
  if (conn.lastScanAt && Date.now() - conn.lastScanAt.getTime() < SCAN_COOLDOWN_MS) return fail("Scanned moments ago. Give it a few seconds.", 429);
  try {
    const scan = await runScan(conn, originOf(request), "manual");
    return json({ scan: { id: scan.id, createdAt: new Date().toISOString(), trigger: "manual", result: scan.result }, connection: view((await owned(user.id, conn.id))!) });
  } catch (err) {
    if (err instanceof AssumeError || err instanceof EngineError) return fail(err.message, 502);
    console.error(err);
    return fail("The scan failed. Try again shortly.", 500);
  }
}
