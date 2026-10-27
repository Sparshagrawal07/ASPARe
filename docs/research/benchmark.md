# Rule-only vs fused triage benchmark

Cases: **17** synthetic, hand-labelled (`data/benchmark/cases.json`).

> **Read this honestly.** Labels were authored by the project, not by independent annotators, and encode the
> intent of the context policy. The set checks that fusion handles situations a severity-only policy cannot
> express (intended-public buckets, scratch data, uncertain evidence, credential-misuse bursts). It is a
> regression benchmark, **not** evidence of real-world accuracy.

| Metric | Rule-only | Fused |
| --- | ---: | ---: |
| Decision accuracy vs label | 0.706 | 1.0 |
| Unsafe auto-remediations (auto-fixed what should not be) | 3 | 0 |
| Missed auto-remediations | 0 | 0 |
| Needless alerts (alert for ignorable finding) | 2 | 0 |
| Precision@7 for urgent findings | 0.571 | 1.0 |

## Per-case decisions

| Case | Expected | Rule-only | Fused | Urgent |
| --- | --- | --- | --- | --- |
| c01 | auto_fix | auto_fix | auto_fix | yes |
| c02 | auto_fix | auto_fix | auto_fix | yes |
| c03 | auto_fix | auto_fix | auto_fix |  |
| c04 | alert | auto_fix | alert |  |
| c05 | alert | auto_fix | alert |  |
| c06 | ignore | alert | ignore |  |
| c07 | ignore | alert | ignore |  |
| c08 | auto_fix | auto_fix | auto_fix | yes |
| c09 | alert | alert | alert |  |
| c10 | auto_fix | auto_fix | auto_fix |  |
| c11 | auto_fix | auto_fix | auto_fix | yes |
| c12 | auto_fix | auto_fix | auto_fix | yes |
| c13 | auto_fix | auto_fix | auto_fix | yes |
| c14 | auto_fix | auto_fix | auto_fix | yes |
| c15 | auto_fix | auto_fix | auto_fix |  |
| c16 | alert | auto_fix | alert |  |
| c17 | alert | alert | alert |  |
