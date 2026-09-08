# ASPARe documentation

> Technical documentation for the deterministic 50% milestone of **ASPARe — Automated Security Posture Assessment & Remediation Engine**.

This documentation is written for a professor evaluating the implementation, a developer reviewing the code, a security engineer analyzing the architecture, and a student presenting the project.

## Start here

1. [Architecture overview](architecture/overview.md) — original prototype versus ASPARe, and why the layers exist.
2. [Implementation status](IMPLEMENTATION_STATUS.md) — what actually works.
3. [Demo guide](DEMO_GUIDE.md) — reproduce detection → remediation → verification without guessing.
4. [Glossary](GLOSSARY.md) — CSPM, findings, verification, and project-specific terms.

## Architecture

- [Event flow](architecture/event-flow.md)
- [Detection engine](architecture/detection-engine.md)
- [Remediation engine](architecture/remediation-engine.md)
- [Verification](architecture/verification.md)
- [Infrastructure](architecture/infrastructure.md)

## Security

- [Threat model](security/threat-model.md)
- [Permissions](security/permissions.md)
- [Attack scenarios](security/attack-scenarios.md)
- [Security controls](security/security-controls.md)

## Implementation

- [Detection rules](implementation/detection-rules.md)
- [Remediation rules](implementation/remediation-rules.md)
- [Risk engine](implementation/risk-engine.md)
- [Audit system](implementation/audit-system.md)

## Testing and roadmap

- [Testing strategy](testing/strategy.md)
- [Unit tests](testing/unit-tests.md)
- [Integration tests](testing/integration-tests.md)
- [Future work](roadmap/future-work.md)

## Review I traceability

| Review I objective | Current 50% | Remaining 50% |
| --- | --- | --- |
| Discovery & authentication | AWS S3 inventory + env credentials | Multi-cloud auth brokers |
| Security assessment & scanning | Direct, scheduled, CloudTrail scans | Distributed scanning |
| Misconfiguration detection | Five S3 rules | Expanded CSPM library |
| Policy Knowledge Base | Versioned JSON registry | LLM-assisted policy authoring |
| Remediation & policy generation | Reviewed parameterized actions | Dynamic least-privilege generation |
| Manual assessment / dashboard | Streamlit read-only view | Approval workflow |
| Automated remediation | Critical/High auto-fixable findings | Broader, policy-profile driven actions |
| Logging & alerting | Structured audit + CloudWatch prints | Production alerting |
| LLM / anomaly / false-positive reduction | Evidence schemas only | Intelligent layer |
| AWS / GCP / Azure | AWS S3 implemented | Azure Blob + GCS |
