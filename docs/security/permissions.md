# Permissions

> Least privilege is a design constraint: the process that classifies a bucket must not be the process that rewrites its policy unless a second role and a second invocation are used.

## Overview

Local/mocked mode uses whatever credentials boto3 finds, further constrained by the application allowlist. Deployed mode uses two IAM roles from [`infrastructure/aws/template.yaml`](../../infrastructure/aws/template.yaml).

## Detection role

Read-only against the allowlisted bucket:

- `s3:ListAllMyBuckets`, `s3:ListBucket`, `s3:HeadBucket`, `s3:GetBucketLocation`
- `s3:GetBucketTagging`, `s3:GetBucketAcl`, `s3:GetBucketPolicy`
- `s3:GetBucketVersioning`, `s3:GetBucketEncryption`
- `s3:GetBucketPublicAccessBlock`, `s3:GetBucketOwnershipControls`
- `s3:PutObject` on `audit/*` of the audit bucket only
- `events:PutEvents` on the ASPARe finding bus
- CloudWatch log writes

## Remediation role

Detection reads plus:

- `s3:PutBucketPublicAccessBlock`
- `s3:PutBucketEncryption`
- `s3:PutBucketVersioning`
- `s3:PutBucketPolicy`
- `s3:PutBucketAcl`

No `s3:DeleteBucket`, `s3:DeleteBucketPolicy`, `iam:*`, or `ec2:*`.

## Resources that may be modified

Only the parameter `AllowedBucketName`, and only if it also carries `ASPAReDemo=true` when that setting is enabled. The live demo creates `aspare-demo-<random>` rather than targeting an existing student or production bucket.

## Operations are destructive?

They are **mutating but scoped**: they enable security controls and merge a known policy statement. They do not empty buckets or delete the original prototype’s “delete any policy” behavior.

## Testing

Integration tests assert a non-allowlisted bucket is not mutated.

## Future improvements

ABAC on additional tags, SCPs, and permission boundaries.
