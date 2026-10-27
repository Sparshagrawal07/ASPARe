import { boolean, integer, pgTable, text, timestamp, uniqueIndex } from "drizzle-orm/pg-core";

// --- Better Auth core tables --------------------------------------------------------------------------------------
export const user = pgTable("user", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const session = pgTable("session", {
  id: text("id").primaryKey(),
  expiresAt: timestamp("expires_at").notNull(),
  token: text("token").notNull().unique(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  userId: text("user_id").notNull().references(() => user.id, { onDelete: "cascade" }),
});

export const account = pgTable("account", {
  id: text("id").primaryKey(),
  accountId: text("account_id").notNull(),
  providerId: text("provider_id").notNull(),
  userId: text("user_id").notNull().references(() => user.id, { onDelete: "cascade" }),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  idToken: text("id_token"),
  accessTokenExpiresAt: timestamp("access_token_expires_at"),
  refreshTokenExpiresAt: timestamp("refresh_token_expires_at"),
  scope: text("scope"),
  password: text("password"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const verification = pgTable("verification", {
  id: text("id").primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: timestamp("expires_at").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

// --- ASPARe product tables ----------------------------------------------------------------------------------------
export const connections = pgTable("connections", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => user.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(), // "aws"
  accountId: text("account_id").notNull(),
  name: text("name").notNull(),
  roleName: text("role_name").notNull(),
  externalId: text("external_id").notNull(),
  mode: text("mode").notNull().default("monitor"), // "monitor" | "autofix" (fix automatically after each scan)
  fixStatus: text("fix_status").notNull().default("off"), // "off" | "connected" (separate write-capable role)
  region: text("region").notNull().default("us-east-1"),
  allowedBuckets: text("allowed_buckets").notNull().default("[]"), // JSON array
  status: text("status").notNull().default("pending"), // pending | connected | error
  lastError: text("last_error"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  lastVerifiedAt: timestamp("last_verified_at"),
  lastScanAt: timestamp("last_scan_at"),
});

export const scans = pgTable("scans", {
  id: text("id").primaryKey(),
  connectionId: text("connection_id").notNull().references(() => connections.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  trigger: text("trigger").notNull().default("manual"),
  summary: text("summary").notNull(), // JSON
  result: text("result").notNull(), // JSON (findings, inventory, incidents)
});

export const auditLog = pgTable("audit_log", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  connectionId: text("connection_id"),
  at: timestamp("at").notNull().defaultNow(),
  action: text("action").notNull(),
  detail: text("detail").notNull().default("{}"),
});

export const waitlist = pgTable(
  "waitlist",
  {
    id: text("id").primaryKey(),
    userId: text("user_id").notNull(),
    provider: text("provider").notNull(),
    createdAt: timestamp("created_at").notNull().defaultNow(),
    position: integer("position"),
  },
  (t) => [uniqueIndex("waitlist_user_provider").on(t.userId, t.provider)],
);
