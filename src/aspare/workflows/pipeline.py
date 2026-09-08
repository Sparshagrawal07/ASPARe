"""In-process pipeline used by demos and tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspare.core.enums import RiskDecision
from aspare.core.models import DetectionOutcome, Finding, RemediationOutcome
from aspare.workflows.detection import DetectionWorkflow
from aspare.workflows.publishers import InProcessPublisher
from aspare.workflows.remediation import RemediationWorkflow


@dataclass
class PipelineResult:
    detection: DetectionOutcome
    remediations: list[RemediationOutcome] = field(default_factory=list)

    def finding_by_rule(self, rule_id: str) -> Finding | None:
        for item in self.detection.findings:
            if item.rule_id == rule_id:
                return item
        return None


class Pipeline:
    def __init__(
        self,
        detection: DetectionWorkflow,
        remediation: RemediationWorkflow,
        publisher: InProcessPublisher,
    ) -> None:
        self._detection = detection
        self._remediation = remediation
        self._publisher = publisher

    def run_raw(self, raw_event: dict) -> PipelineResult:
        detection = self._detection.run_raw(raw_event)
        remediations: list[RemediationOutcome] = []
        queued = list(self._publisher.published)
        self._publisher.published.clear()
        for classified in detection.classified:
            if classified.decision is RiskDecision.AUTO_REMEDIATE:
                remediations.append(self._remediation.run(classified.finding))
        for finding in queued:
            if all(item.finding.finding_id != finding.finding_id for item in remediations):
                remediations.append(self._remediation.run(finding))
        return PipelineResult(detection=detection, remediations=remediations)
