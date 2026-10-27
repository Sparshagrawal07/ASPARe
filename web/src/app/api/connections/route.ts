import { desc, eq } from "drizzle-orm";
import { createConnection, createSchema, latestScan, view } from "@/server/connections";
import { getDb } from "@/server/db";
import { fail, json, requireUser } from "@/server/http";
import { connections } from "@/server/schema";

export async function GET(request: Request) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const db = await getDb();
  const rows = await db.select().from(connections).where(eq(connections.userId, user.id)).orderBy(desc(connections.createdAt));
  const out = [];
  for (const c of rows) {
    const scan = await latestScan(c.id);
    out.push({ ...view(c), lastSummary: scan?.result.summary ?? null });
  }
  return json({ connections: out });
}

export async function POST(request: Request) {
  const user = await requireUser(request);
  if (user instanceof Response) return user;
  const parsed = createSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return fail(parsed.error.issues[0]?.message ?? "Invalid request");
  const made = await createConnection(user.id, parsed.data);
  if ("error" in made) return fail(made.error, 409);
  return json({ connection: view(made) }, 201);
}
