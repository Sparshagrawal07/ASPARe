# Demo guide

> Reproduce the ASPARe 50% demonstration without guessing AWS console steps.

## 1. Prerequisites

- Python 3.11+ (3.14 supported)
- `pip`
- Optional live demo: AWS credentials with permission to create one tagged S3 bucket in `us-east-1`

## 2. Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,dashboard]"
```

## 3. AWS configuration

**Mocked mode (default, CI):** no AWS account. moto intercepts boto3.

**Live mode:** `aws configure` or environment variables. ASPARe still refuses to run unless `--confirm ASPARE-LIVE-DEMO` is passed. It creates `aspare-demo-<random>` and tags it `ASPAReDemo=true`. It will not use `ferpa-student-record-demo-for-cap` or any unrelated bucket.

## 4. Create test resource

Mocked mode creates the bucket inside the demo process. You do not create one manually.

## 5. Introduce misconfiguration

The demo writes Public Access Block flags to false, omits default encryption, omits versioning, omits HTTPS Deny, and attempts a public ACL when the API allows it.

## 6. Trigger detection

```bash
python -m aspare.cli --mode mocked
```

Equivalent: `python scripts/demo.py --mode mocked`

## 7. Observe finding

Stdout lists findings. Expect `S3_PUBLIC_ACCESS` (CRITICAL) and `S3_HTTPS_ENFORCEMENT_MISSING` (HIGH) at minimum.

## 8. Observe automated remediation

The same process remediates AUTO_REMEDIATE findings. Public access and HTTPS should reach `REMEDIATED` with `verified: true`. Versioning should remain `ALERT_AND_LOG`.

## 9. Verify resource

Verification is automatic (re-read + re-run rule). The summary `acceptance` object records whether public-access and HTTPS paths succeeded.

## 10. View audit record

```bash
less var/audit/aspare.jsonl
```

Each line is one `AuditRecord`.

## 11. View dashboard

```bash
streamlit run dashboard/app.py
```

Open the printed local URL. Confirm summary cards, findings columns (Resource, Rule, Severity, Status, Detected At, Remediation, Verification), and recent activity (resource, issue, action, result, verified, timestamp).

No screenshots are checked in; do not treat placeholders as evidence.

## Live demo

```bash
python -m aspare.cli --mode live --confirm ASPARE-LIVE-DEMO --cleanup
```

`--cleanup` deletes the demo bucket after the run when possible.
