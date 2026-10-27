# Least-privilege policy generation

> ASPARe's own IAM roles should hold only what the code actually does. The generator derives them and a test proves the
> derivation complete.

## Overview

`aspare.policygen.generate_policies(buckets, ...)` returns a detection policy (read-only) and a remediation policy
(read plus only the write APIs behind the remediation actions in scope), scoped to exact bucket ARNs. It refuses an
empty bucket list because ASPARe never gets account-wide write access.

## How it works

The action table maps each remediation action to its IAM write permission. `s3:ListAllMyBuckets` (not resource-scopable)
is granted to the detection role only. Optional audit-bucket write (`audit/*`), SNS publish, EventBridge `PutEvents` and
log-group statements are added when their ARNs are supplied. Each statement has a rationale and the result carries a human
review checklist. `validate_least_privilege` rejects wildcard actions and resources.

## Security considerations

Generated policies are proposals for review, never applied automatically. Two tests keep them honest:

- A recording test runs the inspector and every remediation action while capturing the real S3 API operations, and fails
  if the generated policies would deny any of them. It caught naming mismatches (`PutPublicAccessBlock` is the IAM action
  `s3:PutBucketPublicAccessBlock`).
- A drift test fails if the CloudFormation roles grant a different S3 action set than the generator says is needed.

## Example

```bash
python -m aspare.cli --mode policy --bucket my-bucket --audit-bucket my-audit-bucket
```

## Testing

`tests/unit/test_policygen.py`.

## Future improvements

Generate Azure RBAC and GCP IAM role definitions the same way, and feed policy simulation results back into the review.
