# Infrastructure

> Demonstration-grade AWS wiring for two Lambdas, a finding bus, an audit bucket, and least-privilege roles. CloudTrail itself is a prerequisite, not something this template fabricates as a production logging estate.

## Overview

[`infrastructure/aws/template.yaml`](../../infrastructure/aws/template.yaml) deploys:

| Component | Purpose |
| --- | --- |
| `aspare-detection` Lambda | Normalize, inspect, detect, classify, publish |
| `aspare-remediation` Lambda | Execute one action, verify, audit |
| `aspare-findings` event bus | AUTO_REMEDIATE findings only |
| Audit S3 bucket | Append-only JSON audit objects |
| Detection/remediation IAM roles | Split read vs write |
| EventBridge rules | Narrow S3 event names; optional hourly scan |
| CloudWatch log groups | 30-day retained logs |

The Streamlit dashboard is **not** deployed. It reads local JSONL or the audit bucket from a workstation.

## Architecture

```mermaid
flowchart TB
    Trail[ExistingCloudTrailTrail] --> DefaultBus[DefaultEventBus]
    DefaultBus --> DetectRule[aspare-s3-detection]
    DetectRule --> DetectFn[aspare-detection]
    DetectFn --> FindBus[aspare-findings]
    FindBus --> RemediateFn[aspare-remediation]
    DetectFn --> Audit[AuditBucket]
    RemediateFn --> Audit
    DetectFn --> CW[/aws/lambda/aspare-detection]
    RemediateFn --> CW2[/aws/lambda/aspare-remediation]
    DetectRole[aspare-detection-role] --> DetectFn
    RemediateRole[aspare-remediation-role] --> RemediateFn
    RemediateFn --> DemoBucket[AllowlistedDemoBucket]
    DetectFn --> DemoBucket
```

## How it works

1. Package `src/` (and `config/` via `ASPARE_POLICY_PATH`) into a zip, upload to `CodeBucket/CodeKey`.
2. Deploy the template with `AllowedBucketName` set to the demo bucket only.
3. Leave `DetectionRuleState=DISABLED` until the demo tag and allowlist are confirmed.
4. Enable CloudTrail management events in the account if they are not already flowing to the default bus.

## Security considerations

Trust boundary: Lambda service principal assumes the roles. The detection role cannot put bucket policies. Both roles can write only `audit/*` on the audit bucket. Remediation writes are scoped to the allowed bucket ARN.

## Failure scenarios

There is no production DLQ in this milestone. Audit persistence failure raises from the handler. Platform retries may re-run idempotent actions.

## Example

```bash
aws cloudformation validate-template \
  --template-body file://infrastructure/aws/template.yaml \
  --region us-east-1
```

SAM is not required. Full deploy needs a packaged zip; the local mocked demo does not.

## Testing

CI asserts handler names and event-name filters exist in the template. Live deploy is not claimed by tests.

## Future improvements

Trail lifecycle, KMS CMK, VPC endpoints, alarms, and DLQs are remaining-50% hardening.
