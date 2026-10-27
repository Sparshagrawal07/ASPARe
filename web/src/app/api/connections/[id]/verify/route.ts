import { z } from "zod";
import { owned, verify, view } from "@/server/connections";
import { fail, json, requireUser } from "@/server/http";

type Ctx = { params: Promise<{ id: string }> };

export async function POST(request: Request, ctx: Ctx) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const conn = await owned(user.id, (await ctx.params).id);
  if (!conn) return fail("Not found", 404);
  const body = z.object({ kind: z.enum(["access", "autofix"]) }).safeParse(await request.json().catch(() => null));
  if (!body.success) return fail("kind must be access or autofix");
  const result = await verify(conn, body.data.kind);
  return json({ ...result, connection: view((await owned(user.id, conn.id))!) });
}
