# Remediation rules

> Reviewed, parameterized actions. This milestone does not generate novel IAM policies.

## Overview

Actions under `aspare.remediation.actions.s3` call `StorageRemediator` after `SafetyGate`.

## Actions

### S3_BLOCK_PUBLIC_ACCESS

Sets `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, and `RestrictPublicBuckets` to true.

### S3_ENABLE_DEFAULT_ENCRYPTION

Puts bucket encryption with `ASPARE_ENCRYPTION_ALGORITHM` (default AES256) or KMS when configured.

### S3_ENABLE_VERSIONING

Puts versioning `Enabled`. Not auto-invoked by the default MEDIUM policy.

### S3_ENFORCE_HTTPS

Merges Sid `ASPAReDenyInsecureTransport`. Other statements remain. Does **not** `DeleteBucketPolicy`.

### S3_REMOVE_PUBLIC_ACL

Drops grants whose URI is AllUsers or AuthenticatedUsers. Owner and canonical grants remain.

## Testing

HTTPS merge preservation is unit-tested. End-to-end public + HTTPS paths are integration-tested.

## Future improvements

LLM-drafted least-privilege statements with human approval.
