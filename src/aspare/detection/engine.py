"""Registry-driven detection engine. Detectors never receive write adapters."""

from __future__ import annotations

from aspare.core.ids import finding_id
from aspare.core.interfaces import DetectionRule
from aspare.core.models import Finding, StorageEvent, StorageResource


class DetectionEngine:
    def __init__(self, rules: list[DetectionRule]) -> None:
        self._rules = list(rules)
        self._by_id = {rule.rule_id: rule for rule in self._rules}

    def evaluate(
        self, resource: StorageResource, event: StorageEvent | None = None
    ) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self._rules:
            if not rule.supports(resource):
                continue
            finding = rule.detect(resource)
            if finding is None:
                continue
            self._bind_event(finding, event)
            findings.append(finding)
        return findings

    def evaluate_rule(
        self, rule_id: str, resource: StorageResource, event: StorageEvent | None = None
    ) -> Finding | None:
        rule = self._by_id.get(rule_id)
        if rule is None or not rule.supports(resource):
            return None
        finding = rule.detect(resource)
        if finding is not None:
            self._bind_event(finding, event)
        return finding

    @staticmethod
    def _bind_event(finding: Finding, event: StorageEvent | None) -> None:
        if event is None:
            return
        finding.event_id = event.event_id
        finding.correlation_id = event.correlation_id
        finding.finding_id = finding_id(finding.resource_id, finding.rule_id, event.event_id)

    def rules(self) -> list[DetectionRule]:
        return list(self._rules)
