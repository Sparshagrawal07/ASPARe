import { drizzle as drizzlePg } from "drizzle-orm/node-postgres";
import type { NodePgDatabase } from "drizzle-orm/node-postgres";
import { sql } from "drizzle-orm";
import * as schema from "./schema";

export type Db = NodePgDatabase<typeof schema>;

const DDL = `
CREATE TABLE IF NOT EXISTS "user" (id text PRIMARY KEY, name text NOT NULL, email text NOT NULL UNIQUE,
  email_verified boolean NOT NULL DEFAULT false, image text, created_at timestamp NOT NULL DEFAULT now(), updated_at timestamp NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS session (id text PRIMARY KEY, expires_at timestamp NOT NULL, token text NOT NULL UNIQUE,
  created_at timestamp NOT NULL DEFAULT now(), updated_at timestamp NOT NULL DEFAULT now(), ip_address text, user_agent text,
  user_id text NOT NULL REFERENCES "user"(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS account (id text PRIMARY KEY, account_id text NOT NULL, provider_id text NOT NULL,
  user_id text NOT NULL REFERENCES "user"(id) ON DELETE CASCADE, access_token text, refresh_token text, id_token text,
  access_token_expires_at timestamp, refresh_token_expires_at timestamp, scope text, password text,
  created_at timestamp NOT NULL DEFAULT now(), updated_at timestamp NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS verification (id text PRIMARY KEY, identifier text NOT NULL, value text NOT NULL,
  expires_at timestamp NOT NULL, created_at timestamp NOT NULL DEFAULT now(), updated_at timestamp NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS connections (id text PRIMARY KEY, user_id text NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  provider text NOT NULL, account_id text NOT NULL, name text NOT NULL, role_name text NOT NULL, external_id text NOT NULL,
  mode text NOT NULL DEFAULT 'monitor', fix_status text NOT NULL DEFAULT 'off', region text NOT NULL DEFAULT 'us-east-1', allowed_buckets text NOT NULL DEFAULT '[]',
  status text NOT NULL DEFAULT 'pending', last_error text, created_at timestamp NOT NULL DEFAULT now(),
  last_verified_at timestamp, last_scan_at timestamp);
CREATE TABLE IF NOT EXISTS scans (id text PRIMARY KEY, connection_id text NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
  created_at timestamp NOT NULL DEFAULT now(), trigger text NOT NULL DEFAULT 'manual', summary text NOT NULL, result text NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (id text PRIMARY KEY, user_id text NOT NULL, connection_id text,
  at timestamp NOT NULL DEFAULT now(), action text NOT NULL, detail text NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS waitlist (id text PRIMARY KEY, user_id text NOT NULL, provider text NOT NULL,
  created_at timestamp NOT NULL DEFAULT now(), position integer);
CREATE UNIQUE INDEX IF NOT EXISTS waitlist_user_provider ON waitlist (user_id, provider);
CREATE INDEX IF NOT EXISTS connections_user ON connections (user_id);
CREATE INDEX IF NOT EXISTS scans_connection ON scans (connection_id, created_at DESC);
`;

type Holder = { db: Db; ready: Promise<void> };
const globalForDb = globalThis as unknown as { __asparedb?: Holder };

async function create(): Promise<Holder> {
  const url = process.env.DATABASE_URL;
  if (url) {
    const { Pool } = await import("pg");
    const pool = new Pool({ connectionString: url, max: 4, idleTimeoutMillis: 10_000 });
    const db = drizzlePg(pool, { schema }) as Db;
    return { db, ready: db.execute(sql.raw(DDL)).then(() => undefined) };
  }
  // Local development and tests: embedded Postgres, no install and no account.
  const { PGlite } = await import("@electric-sql/pglite");
  const { drizzle } = await import("drizzle-orm/pglite");
  const dir = process.env.PGLITE_DIR ?? "./.data/pglite";
  (await import("node:fs")).mkdirSync(dir, { recursive: true });
  const lite = new PGlite(dir);
  const db = drizzle(lite, { schema }) as unknown as Db;
  return { db, ready: lite.exec(DDL).then(() => undefined) };
}

let pending: Promise<Holder> | undefined;

/** The database, with the schema guaranteed to exist. Safe to call on every request. */
export async function getDb(): Promise<Db> {
  try {
    if (!globalForDb.__asparedb) {
      pending ??= create();
      globalForDb.__asparedb = await pending;
    }
    await globalForDb.__asparedb.ready;
    return globalForDb.__asparedb.db;
  } catch (err) {
    // A failed start must not poison later requests.
    globalForDb.__asparedb = undefined;
    pending = undefined;
    throw err;
  }
}
