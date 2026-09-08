# Testing strategy

> The 50% milestone is proven with in-memory rule tests and moto-backed AWS tests. Live AWS is optional and never required for CI.

## Overview

| Layer | Location | AWS |
| --- | --- | --- |
| Unit | `tests/unit/` | none |
| Mocked integration | `tests/integration/` | moto |
| Demo smoke | `python -m aspare.cli --mode mocked` | moto |
| Docs | `tests/check_docs.py` | none |

## Fixtures

Secure, public, unencrypted, versioning-disabled, missing-HTTPS, and unsafe-ACL buckets in `tests/fixtures/builders.py`, plus a CloudTrail EventBridge payload.

## CI

`.github/workflows/ci.yml` runs ruff, pytest, template marker checks, documentation presence, and the mocked demo.

## Future improvements

Contract tests against recorded AWS responses and research benchmarks in the remaining 50%.
