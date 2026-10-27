import { eq } from "drizzle-orm";
import { currentUser } from "@/server/auth";
import { getDb } from "@/server/db";
import { json, requireUser } from "@/server/http";
import { auditLog, user as userTable, waitlist } from "@/server/schema";

export async function GET(request: Request) {
  return json({ user: await currentUser(request.headers) });
}

/** Erase the account and everything linked to it (connections, scans, sessions, audit entries, waitlist). */
export async function DELETE(request: Request) {
  const me = await requireUser(request);
  if (me instanceof Response) return me;
  const db = await getDb();
  await db.delete(auditLog).where(eq(auditLog.userId, me.id));
  await db.delete(waitlist).where(eq(waitlist.userId, me.id));
  await db.delete(userTable).where(eq(userTable.id, me.id)); // cascades to sessions, accounts, connections, scans
  return json({ ok: true });
}
