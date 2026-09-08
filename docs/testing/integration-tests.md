# Integration tests

> moto provides an isolated AWS API. The real inspector, remediator, workflows, and handlers run against it.

## Coverage

- public-access and HTTPS end-to-end auto-remediation with verification
- versioning remains `ALERT_AND_LOG` under the default policy
- duplicate delivery is idempotent after the bucket is secured
- Lambda handler JSON serialization
- no mutation of buckets outside the allowlist

## How to run

```bash
pytest tests/integration -q
```

Live AWS is **not** part of CI. Use `python -m aspare.cli --mode live --confirm ASPARE-LIVE-DEMO --cleanup` only with credentials you control.
