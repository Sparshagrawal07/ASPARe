import { z } from "zod";
import { owned, runFix, view } from "@/server/connections";
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
  const body = z.object({ findingIds: z.array(z.string().max(64)).min(1).max(50) }).safeParse(await request.json().catch(() => null));
  if (!body.success) return fail("Choose at least one finding");
  try {
    const out = await runFix(conn, body.data.findingIds, originOf(request));
    return json({
      outcomes: out.outcomes,
      refused: out.refused,
      scan: { id: out.scan.id, createdAt: new Date().toISOString(), trigger: "manual", result: out.scan.result },
      connection: view((await owned(user.id, conn.id))!),
    });
  } catch (err) {
    if (err instanceof AssumeError || err instanceof EngineError) return fail(err.message, 502);
    console.error(err);
    return fail("The fix failed. Nothing was left half-applied that a re-scan will not show.", 500);
  }
}
