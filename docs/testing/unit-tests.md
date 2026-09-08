# Unit tests

> Rules, risk, events, audit, verification, and safety gates run without AWS credentials.

## Coverage

- public access, encryption, versioning, HTTPS, ACL detection
- secure-bucket negatives and BucketOwnerEnforced ACL exception
- severity evaluation and alternate risk policies
- remediation selection, unsupported actions, allowlist denial
- verification success, action failure, re-read failure, persistent finding
- audit record round-trip
- CloudTrail / scheduled / demo normalization
- Policy Knowledge Base integrity

## How to run

```bash
pytest tests/unit -q
```
