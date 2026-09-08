# Audit system

> Every scan, finding, decision, action, and verification becomes an `AuditRecord`. Console `print` is not the system of record.

## Overview

Backends: in-memory (tests), JSONL (`var/audit/aspare.jsonl`), S3 (`audit/YYYY/MM/DD/<id>.json`). `FallbackAuditRepository` writes a structured log and raises if the primary store fails.

## Record fields

`record_id`, `timestamp`, `resource_id`, `finding_id`, `rule_id`, `policy_id`, `severity`, `action`, `result`, `verified`, `before_state`, `after_state`, `actor`, `correlation_id`, `event_id`, `details`.

## Reporting

`ReportingAggregator` folds the append-only stream into latest finding rows and remediation activity for the dashboard.

## Testing

`tests/unit/test_audit.py` plus integration assertions that verification records exist.

## Future improvements

Athena views, integrity hashing, and WORM Object Lock.
