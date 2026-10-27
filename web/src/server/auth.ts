import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { nextCookies } from "better-auth/next-js";
import { getDb } from "./db";
import * as schema from "./schema";

function baseUrl(): string {
  if (process.env.BETTER_AUTH_URL) return process.env.BETTER_AUTH_URL;
  if (process.env.VERCEL_PROJECT_PRODUCTION_URL) return `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://localhost:3000";
}

let cached: ReturnType<typeof build> | undefined;

async function build() {
  const db = await getDb();
  const social: Record<string, { clientId: string; clientSecret: string }> = {};
  if (process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET)
    social.github = { clientId: process.env.GITHUB_CLIENT_ID, clientSecret: process.env.GITHUB_CLIENT_SECRET };
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET)
    social.google = { clientId: process.env.GOOGLE_CLIENT_ID, clientSecret: process.env.GOOGLE_CLIENT_SECRET };
  return betterAuth({
    baseURL: baseUrl(),
    secret: process.env.BETTER_AUTH_SECRET,
    database: drizzleAdapter(db, { provider: "pg", schema }),
    emailAndPassword: { enabled: true, minPasswordLength: 10, maxPasswordLength: 128, autoSignIn: true },
    socialProviders: social,
    session: { expiresIn: 60 * 60 * 24 * 14, updateAge: 60 * 60 * 24 },
    rateLimit: { enabled: true, window: 60, max: 30 },
    trustedOrigins: [baseUrl(), ...(process.env.VERCEL_URL ? [`https://${process.env.VERCEL_URL}`] : [])],
    plugins: [nextCookies()],
  });
}

/** Better Auth instance, created once per server instance. */
export function getAuth() {
  cached ??= build();
  return cached;
}

export async function currentUser(headers: Headers) {
  const auth = await getAuth();
  const s = await auth.api.getSession({ headers });
  return s?.user ? { id: s.user.id, email: s.user.email, name: s.user.name } : null;
}

export function enabledSocial() {
  return {
    github: Boolean(process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET),
    google: Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET),
  };
}
