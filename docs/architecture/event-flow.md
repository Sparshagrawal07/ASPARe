# Event flow

> Every AWS, scheduled, or demo input is reduced to a `StorageEvent` before inventory or detection runs.

## Overview

The original remediator consumed `event["detail"]` directly. ASPARe parsers emit a provider-neutral event with `provider`, `event_type`, `resource_type`, `resource_id`, `actor`, `timestamp`, `correlation_id`, and `metadata`.

## Architecture

```mermaid
flowchart TB
    Incoming[IncomingEvent] --> Identify[IdentifyResource]
    Identify --> Load[LoadResourceConfiguration]
    Load --> Execute[ExecuteDetectionRules]
    Execute --> Decision{AnyViolation}
    Decision -->|yes| Finding[NormalizedFinding]
    Decision -->|no| Clean[CleanScanAudit]
    Finding --> Risk[RiskEvaluation]
    Risk --> Branch{Decision}
    Branch -->|AUTO_REMEDIATE| Publish[PublishFinding]
    Branch -->|ALERT_AND_LOG or LOG_ONLY| AuditOnly[AuditAndDashboard]
```

## How it works

### Step 1 — Parse

`EventNormalizer` routes on `source` / `detail-type`:

- `AWS API Call via CloudTrail` → CloudTrail parser (S3 bucket from `requestParameters.bucketName`)
- `aspare.scheduler` → one event per bucket, or `resource_id=*` for allowlist inventory
- `aspare.demo` / direct scan → bucket from `detail.bucket`

### Step 2 — Inventory

`InventoryService` asks the AWS S3 inspector for a snapshot: Public Access Block, encryption, versioning, policy, ACL, ownership, tags. Missing configurations are distinguished from `ClientError` permission failures.

### Step 3 — Detect and classify

The detection engine runs every supporting rule. Risk evaluation assigns `AUTO_REMEDIATE`, `ALERT_AND_LOG`, `LOG_ONLY`, or `MANUAL_REVIEW`.

## Event-driven AWS path

```mermaid
flowchart TB
    S3[S3BucketAPIs] -->|"control: management event"| CloudTrail[CloudTrail]
    CloudTrail -->|"data: AWS API Call via CloudTrail"| DefaultBus[DefaultEventBus]
    DefaultBus -->|"control: filtered eventName"| DetectionFn[aspare-detection]
    DetectionFn -->|"data: StorageEvent"| Normalizer[EventNormalizer]
    DetectionFn -->|"control: PutEvents AUTO_REMEDIATE"| FindingBus[ASPAReEventBus]
    FindingBus -->|"control: finding payload"| RemediationFn[aspare-remediation]
    RemediationFn -->|"control: S3 write APIs"| S3
    DetectionFn -->|"data: AuditRecord"| AuditBucket[AuditBucket]
    RemediationFn -->|"data: AuditRecord"| AuditBucket
    DetectionFn -->|"data: logs"| CW[CloudWatchLogs]
    RemediationFn -->|"data: logs"| CW
    IAMDetect[DetectionRole] -->|"trust: lambda.amazonaws.com"| DetectionFn
    IAMRem[RemediationRole] -->|"trust: lambda.amazonaws.com"| RemediationFn
```

Control flow is EventBridge → Lambda. Data flow is snapshots, findings, and audit JSON. They are intentionally not the same arrows: detection can fail closed without writing to S3 storage buckets.

## Failure scenarios

```mermaid
flowchart TB
    DetectFail[DetectionFailure] --> Log[StructuredErrorLog]
    Log --> AuditFail[ScanCompleted FAILED]
    AuditFail --> Retry[PlatformRetryOrDLQ]
```

If CloudTrail delivery is delayed, the scheduled scan still inspects the allowlisted bucket. ASPARe assumes at-least-once delivery; finding IDs are deterministic per resource + rule + event.

## Example

A `PutBucketPublicAccessBlock` CloudTrail event with `bucketName=demo-bucket` becomes:

```text
provider=aws
event_type=cloudtrail_api_call
resource_type=s3_bucket
resource_id=demo-bucket
actor=arn:aws:iam::...:user/...
```

## Testing

See `tests/unit/test_events.py` and the CloudTrail fixture `tests/fixtures/cloudtrail_put_pab.json`.

## Future improvements

Remaining 50%: EventBridge archive/replay, SQS buffers, and multi-account event buses.
