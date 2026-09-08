# Risk engine

> Severity comes from the Policy Knowledge Base. Response comes from [`config/risk-policy.json`](../../config/risk-policy.json). `scoring.py` is a transparent weight table, not an anomaly model.

## Overview

Default mapping:

| Severity | Auto-remediable | Decision |
| --- | --- | --- |
| CRITICAL | yes | AUTO_REMEDIATE |
| HIGH | yes | AUTO_REMEDIATE |
| MEDIUM | yes | ALERT_AND_LOG |
| LOW | yes | LOG_ONLY |
| any | no | MANUAL_REVIEW |

Weights: CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25. They are **not** confidence scores and must not be presented as machine learning.

## How it works

`RiskEvaluator.evaluate(finding)` reads only severity and `auto_remediable`. Changing organizational appetite is a JSON edit, not a rule rewrite.

## Testing

`tests/unit/test_risk.py`.

## Future improvements

Compliance profiles (CIS vs internal) and human approval for High.
