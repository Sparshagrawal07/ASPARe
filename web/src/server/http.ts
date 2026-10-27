import { currentUser } from "./auth";

export function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "Cache-Control": "no-store" } });
}

export function fail(message: string, status = 400): Response {
  return json({ error: message }, status);
}

/** Mutating requests must come from our own pages (defence in depth on top of SameSite cookies). */
export function sameOrigin(req: Request): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return true; // non-browser callers (cron, curl) carry no cookies to abuse
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export async function requireUser(req: Request): Promise<{ id: string; email: string; name: string } | Response> {
  if (!sameOrigin(req)) return fail("Cross-origin request blocked", 403);
  const user = await currentUser(req.headers);
  return user ?? fail("Please sign in", 401);
}

export function originOf(req: Request): string {
  const proto = req.headers.get("x-forwarded-proto") ?? "http";
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? "localhost:3000";
  return `${proto}://${host}`;
}
