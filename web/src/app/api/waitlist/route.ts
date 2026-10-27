import { randomUUID } from "node:crypto";
import { z } from "zod";
import { getDb } from "@/server/db";
import { fail, json, requireUser } from "@/server/http";
import { waitlist } from "@/server/schema";

export async function POST(request: Request) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const body = z.object({ provider: z.enum(["azure", "gcp"]) }).safeParse(await request.json().catch(() => null));
  if (!body.success) return fail("provider must be azure or gcp");
  const db = await getDb();
  await db.insert(waitlist).values({ id: randomUUID(), userId: user.id, provider: body.data.provider }).onConflictDoNothing();
  return json({ ok: true });
}
