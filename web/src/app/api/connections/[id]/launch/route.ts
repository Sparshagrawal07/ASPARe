import { z } from "zod";
import { launchStack, owned } from "@/server/connections";
import { fail, json, requireUser } from "@/server/http";

type Ctx = { params: Promise<{ id: string }> };

export async function POST(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  const body = z.object({ kind: z.enum(["access", "autofix"]) }).safeParse(await request.json().catch(() => null));
  if (!body.success) return fail("kind must be access or autofix");
  try {
    return json(await launchStack(conn, body.data.kind));
  } catch (err) {
    return fail((err as Error).message, 503);
  }
}
