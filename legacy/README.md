# Legacy prototype

The original course prototype (a single-script IAM / security-group / S3 scanner) was retired when ASPARe was
rebuilt as a layered, tested platform. It is intentionally **not** part of this repository any more: it mutated
resources without an allowlist, verification, or audit trail.

Everything it did is covered by the current architecture:

| Prototype behaviour | ASPARe replacement |
| --- | --- |
| Ad-hoc S3 checks | Policy-driven detection rules (`src/aspare/detection/rules/s3`) |
| Direct fixes | Allowlisted, tag-gated remediation actions with post-write verification |
| `print` output | Structured JSONL / S3 audit trail and the Streamlit dashboard |

IAM and security-group checks are listed under future work in
[`docs/roadmap/future-work.md`](../docs/roadmap/future-work.md).
