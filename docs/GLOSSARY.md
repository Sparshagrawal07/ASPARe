# Glossary

> Terms as used in ASPARe’s deterministic 50% milestone.

**ASPARe** — Automated Security Posture Assessment & Remediation Engine; this project.

**ACL** — Access Control List on an S3 bucket or object. Public URIs `AllUsers` and `AuthenticatedUsers` are treated as unsafe grants.

**Audit record** — Immutable structured event describing a scan, finding, decision, action, or verification.

**CloudTrail** — AWS API audit log. ASPARe consumes management events via EventBridge. An enabled trail is a deploy prerequisite.

**Configuration drift** — A later change reintroduces a misconfiguration after a verified remediation.

**CSPM** — Cloud Security Posture Management: continuously assessing cloud configuration against policy.

**EventBridge** — AWS event router. ASPARe uses the default bus for CloudTrail matches and a dedicated bus for AUTO_REMEDIATE findings.

**Finding** — Normalized detection result (`rule_id`, `severity`, `resource_id`, evidence, action hint).

**IAM** — AWS Identity and Access Management. Prototype IAM-user remediation is legacy-only.

**Infrastructure as code** — The CloudFormation template under `infrastructure/aws/`.

**Least privilege** — Detection cannot write bucket policies; remediation writes are scoped to an allowlisted bucket.

**Policy Knowledge Base** — Versioned JSON registry mapping controls to rules, severity, and actions. Not an LLM.

**Remediation** — Applying a reviewed action to a finding. Distinct from detection.

**S3** — Amazon Simple Storage Service; the only fully implemented provider in this milestone.

**Severity** — CRITICAL/HIGH/MEDIUM/LOW from the policy registry. Not an anomaly score.

**Verification** — Re-inventory plus re-running the originating rule after an action.

**Internal codename** — Early planning notes used “CloudSentinel” for this repository folder; the product name is ASPARe.
