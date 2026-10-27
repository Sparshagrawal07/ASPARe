# Implementation status

> Honest status of ASPARe. "Verified" says how each item was checked; read it before presenting a claim.

## Completed

- AWS S3 discovery/inventory (`S3Inspector`)
- CloudTrail, scheduled, and demo event normalization
- Policy Knowledge Base (`config/policies/s3.json` + `PolicyRegistry`)
- Five S3 detection rules and finding normalization
- Risk evaluation from `config/risk-policy.json`
- Five S3 remediation actions with allowlist/demo-tag safety
- Post-remediation verification
- JSONL / memory / S3 audit repositories
- In-process pipeline, split Lambda handlers, CloudFormation template
- Streamlit dashboard: recorded lab and **Live AWS** mode (read-only scan, per-finding approval, dry-run default)
- Live Showcase page: five real-AWS scenarios with streamed reasoning, before/after proof and cleanup
- Manual approval workflow (audited `REMEDIATION_APPROVED`, safety gate still enforced)
- SNS alerting for findings that are not auto-remediated
- Lambda packaging, deploy and teardown scripts; cfn-lint + mypy in CI
- Mocked demo and guarded live demo
- Unit and mocked integration tests
- Replacement documentation; prototype archived under `legacy/`

## Intelligence layer (new)

- **Anomaly scoring** (`aspare.intelligence.anomaly`): privileged actor, risky action, burst, novel actor, off-hours;
  computed from the event stream against a learned baseline; omitted when there is no evidence.
- **Fusion** (`aspare.intelligence.fusion`): evidence-weighted confidence, priority, context rules from
  `config/context-policy.json`, incident correlation. Lowers automatic fixes to alerts; never raises to automatic.
- **LLM reasoner** (`aspare.intelligence.reasoner`): Claude with an offline fallback; advisory only; resource names and
  tags treated as untrusted data.
- **Least-privilege policy generation** (`aspare.policygen`): proven complete by a test that records real API calls.
- **Azure Blob + Google Cloud Storage** adapters with a routing layer, safety gate and verification shared with AWS.
- **Benchmark** (`scripts/benchmark.py`): rule-only vs fused on 17 hand-labelled cases.

## Verification status (be precise)

| Claim | Evidence | Not verified |
| --- | --- | --- |
| AWS S3 detect/fix/verify | Real AWS account runs (Live Showcase, live scan, deployed Lambda chain via manual/scheduled trigger) | |
| Fusion/anomaly behaviour | Unit tests and a synthetic benchmark | Real-world accuracy: labels are project-authored, set is small |
| LLM analysis | Fake-client tests (prompt shape, parsing, refusal/outage fallback) | A live Claude call (needs `ANTHROPIC_API_KEY`) |
| Azure and GCS | Mapping + remediation logic against in-memory APIs | The real SDK wrappers (`providers/azure/sdk.py`, `providers/gcp/sdk.py`) against live Azure/GCP |
| Real-time CloudTrail trigger | Rule pattern tested; trail logging and delivering | **Did not fire within 15 minutes in the test account**; hourly scan is the backstop |

## Known limits

- No dashboard authentication; the dashboard is not hosted.
- Anomaly baseline is in-memory per process (Lambda cold starts relearn); no persistent behavioural store.
- Rule ids keep the `S3_` prefix on Azure/GCS findings for compatibility; GCS has no HTTPS-only control.
- DLQs, multi-account scale and continuous compliance libraries beyond the five storage controls are out of scope.
