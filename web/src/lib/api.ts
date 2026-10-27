export type Cloud = "aws" | "azure" | "gcp";

export type Controls = {
  publicBlocked: boolean;
  encrypted: boolean;
  versioning: boolean;
  https: boolean | null;
  publicGrant: boolean;
};

export type Resource = {
  cloud: Cloud;
  name: string;
  tags: Record<string, string>;
  controls: Controls;
};

export type Change = { resource: string; actor: string; eventName: string; hour: number; minute: number };
export type Estate = { resources: Resource[]; changes: Change[] };

export type Decision = "AUTO_REMEDIATE" | "ALERT_AND_LOG" | "LOG_ONLY" | "MANUAL_REVIEW";

export type Finding = {
  id: string;
  resource: string;
  cloud: Cloud;
  rule: string;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  ruleOnlyDecision: Decision | null;
  decision: Decision | null;
  confidence: number | null;
  priority: number | null;
  reasons: string[];
  contextRules: string[];
  anomaly: { score?: number | null; signals?: { name: string; value: number; explanation: string }[] };
  escalate: boolean;
  what: string;
  affects: string;
  remedy: string;
  remedyDoes: string;
  standards: string[];
  analysis: { summary: string; rootCause: string; recommendation: string };
  canFix: boolean;
};

export type Incident = { id: string; kind: string; resource: string; severity: string; summary: string; count: number };

export type ScanResult = {
  findings: Finding[];
  incidents: Incident[];
  summary: { total: number; auto: number; held: number; escalations: number };
};

export type Outcome = {
  findingId: string;
  resource: string;
  cloud: Cloud;
  rule: string;
  action: string;
  verified: boolean;
  verification: string;
  message: string;
  before: string[];
  after: string[];
};

export type RemediateResult = {
  outcomes: Outcome[];
  estate: Estate;
  audit: { action: string; result: string; resource: string; rule: string | null }[];
};

export type PolicyResult = Record<
  "detection" | "remediation",
  { policy: unknown; rationale: Record<string, string>; reviewChecklist: string[]; problems: string[] }
>;

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ error: "The server sent an unreadable response." }));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data as T;
}

export const api = {
  estate: () => post<Estate>("/api/estate", {}),
  scan: (estate: Estate) => post<ScanResult>("/api/scan", { estate }),
  remediate: (estate: Estate, findingIds: string[]) => post<RemediateResult>("/api/remediate", { estate, findingIds }),
  policy: (buckets: string[], auditBucket?: string) => post<PolicyResult>("/api/policy", { buckets, auditBucket }),
};

export const CLOUD_META: Record<Cloud, { label: string; tone: "sun" | "sky" | "mint" }> = {
  aws: { label: "AWS S3", tone: "sun" },
  azure: { label: "Azure Blob", tone: "sky" },
  gcp: { label: "Google Cloud", tone: "mint" },
};
