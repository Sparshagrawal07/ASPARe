"""Policy-driven risk evaluation. Detectors never decide whether to remediate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aspare.core.enums import RiskDecision, Severity
from aspare.core.models import Finding
from aspare.risk.scoring import DEFAULT_WEIGHTS, severity_weight


@dataclass(frozen=True)
class RiskPolicy:
    auto_remediate_severities: frozenset[Severity]
    alert_severities: frozenset[Severity]
    log_only_severities: frozenset[Severity]
    require_auto_remediable_for_auto: bool
    manual_review_when_not_auto_remediable: bool
    weights: dict[Severity, int]

    @classmethod
    def from_path(cls, path: str | Path) -> RiskPolicy:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict) -> RiskPolicy:
        def _sev(key: str) -> frozenset[Severity]:
            return frozenset(Severity(item) for item in payload.get(key, []))

        raw_weights = payload.get("severity_weights") or {}
        weights = dict(DEFAULT_WEIGHTS)
        for name, value in raw_weights.items():
            weights[Severity(name)] = int(value)
        return cls(
            auto_remediate_severities=_sev("auto_remediate_severities"),
            alert_severities=_sev("alert_severities"),
            log_only_severities=_sev("log_only_severities"),
            require_auto_remediable_for_auto=bool(
                payload.get("require_auto_remediable_for_auto", True)
            ),
            manual_review_when_not_auto_remediable=bool(
                payload.get("manual_review_when_not_auto_remediable", True)
            ),
            weights=weights,
        )

    @classmethod
    def default(cls) -> RiskPolicy:
        return cls(
            auto_remediate_severities=frozenset({Severity.CRITICAL, Severity.HIGH}),
            alert_severities=frozenset({Severity.MEDIUM}),
            log_only_severities=frozenset({Severity.LOW}),
            require_auto_remediable_for_auto=True,
            manual_review_when_not_auto_remediable=True,
            weights=dict(DEFAULT_WEIGHTS),
        )


class RiskEvaluator:
    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy.default()

    def evaluate(self, finding: Finding) -> RiskDecision:
        if self.policy.manual_review_when_not_auto_remediable and not finding.auto_remediable:
            return RiskDecision.MANUAL_REVIEW
        if finding.severity in self.policy.auto_remediate_severities:
            if self.policy.require_auto_remediable_for_auto and not finding.auto_remediable:
                return RiskDecision.MANUAL_REVIEW
            return RiskDecision.AUTO_REMEDIATE
        if finding.severity in self.policy.alert_severities:
            return RiskDecision.ALERT_AND_LOG
        return RiskDecision.LOG_ONLY

    def weight(self, finding: Finding) -> int:
        return severity_weight(finding.severity, self.policy.weights)
