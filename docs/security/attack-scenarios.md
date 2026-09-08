# Attack scenarios

> Concrete stories that exercise ASPARe’s controls and show where the 50% milestone still stops.

## Overview

These scenarios are for evaluation and tabletop use. They are not exploit guides.

## Scenario 1 — Public lab bucket

An operator disables all Public Access Block flags on a tagged demo bucket. CloudTrail or a direct scan produces `S3_PUBLIC_ACCESS` (CRITICAL). Risk selects `AUTO_REMEDIATE`. `S3_BLOCK_PUBLIC_ACCESS` enables the four flags. Verification re-runs the public-access rule. The dashboard shows `REMEDIATED` / verified.

## Scenario 2 — HTTPS missing while PAB is already correct

Only `S3_HTTPS_ENFORCEMENT_MISSING` fires. Remediation merges `ASPAReDenyInsecureTransport` without deleting other statements.

## Scenario 3 — Attacker tries to remediate a production bucket

A CloudTrail event names `prod-data`. Safety gate denies the write because the name is not allowlisted and/or the demo tag is missing. Audit records `DENIED`.

## Scenario 4 — Event spoofing

An IAM user invokes `aspare-detection` with a forged EventBridge-shaped payload. The function may scan, but writes still require allowlist + tag. Residual risk: information disclosure of the demo bucket configuration.

## Scenario 5 — Policy conflict

A bucket policy explicitly allows insecure transport and also contains unrelated statements. ASPARe adds a Deny. If a later change removes the Sid, scheduled scan re-detects drift.

## Scenario 6 — Verification lies if skipped

If verification were skipped (the prototype), a failed `PutBucketPolicy` could still be labelled success. ASPARe treats action failure as `REMEDIATION_FAILED`.

## Testing

Scenario 1 and 2 are automated in `tests/integration/test_mocked_aws.py`. Scenario 3 is the allowlist integration test.

## Future improvements

Object-level ransomware patterns and anomaly-based mass ACL changes wait for the intelligent layer.
