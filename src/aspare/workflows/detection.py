"""Detection workflow: normalize → inventory → detect → classify → audit → publish."""

from __future__ import annotations

from typing import Any

from aspare.audit.repository import build_record
from aspare.core.enums import AuditAction, FindingStatus, RiskDecision
from aspare.core.interfaces import AuditRepository, FindingAlerter, FindingPublisher
from aspare.core.lifecycle import InvalidLifecycleTransition, status_for_decision, transition
from aspare.core.models import ClassifiedFinding, DetectionOutcome, Finding, StorageEvent, StorageResource
from aspare.detection.engine import DetectionEngine
from aspare.events.normalizer import EventNormalizer
from aspare.intelligence.fusion import FusionEngine, FusionResult
from aspare.inventory.service import InventoryService
from aspare.logging import get_logger, log_event
from aspare.risk.evaluator import RiskEvaluator


class DetectionWorkflow:
    def __init__(
        self,
        normalizer: EventNormalizer,
        inventory: InventoryService,
        detection: DetectionEngine,
        risk: RiskEvaluator,
        audit: AuditRepository,
        publisher: FindingPublisher,
        alerter: FindingAlerter | None = None,
        fusion: FusionEngine | None = None,
    ) -> None:
        self._normalizer = normalizer
        self._inventory = inventory
        self._detection = detection
        self._risk = risk
        self._audit = audit
        self._publisher = publisher
        self._alerter = alerter
        self._fusion = fusion
        self._logger = get_logger("aspare.detection")

    def run_raw(self, raw_event: dict) -> DetectionOutcome:
        events = self._normalizer.normalize_many(raw_event)
        combined = DetectionOutcome(event=events[0], resources=[], findings=[], classified=[])
        for event in events:
            outcome = self.run(event)
            combined.resources.extend(outcome.resources)
            combined.findings.extend(outcome.findings)
            combined.classified.extend(outcome.classified)
            combined.errors.extend(outcome.errors)
            combined.event = event
        return combined

    def run(self, event: StorageEvent) -> DetectionOutcome:
        errors: list[str] = []
        try:
            resources = self._inventory.resources_for(event)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            log_event(self._logger, "inventory_failed", error=str(exc), resource=event.resource_id)
            self._audit.append(
                build_record(
                    action=AuditAction.SCAN_COMPLETED.value,
                    result="FAILED",
                    resource_id=event.resource_id,
                    correlation_id=event.correlation_id,
                    actor=event.actor,
                    event_id=event.event_id,
                    details={"error": str(exc)},
                )
            )
            return DetectionOutcome(event=event, resources=[], findings=[], classified=[], errors=errors)

        assessment = self._fusion.observe(event) if self._fusion else None
        findings: list[Finding] = []
        classified: list[ClassifiedFinding] = []
        for resource in resources:
            detected = self._detection.evaluate(resource, event)
            findings.extend(detected)
            for finding in detected:
                self._audit.append(
                    build_record(
                        action=AuditAction.FINDING_DETECTED.value,
                        result="DETECTED",
                        resource_id=resource.resource_id,
                        correlation_id=event.correlation_id,
                        finding=finding,
                        actor=event.actor,
                        event_id=event.event_id,
                    )
                )
                item = self._classify(finding, event.actor, resource, assessment, event)
                classified.append(item)

        self._audit.append(
            build_record(
                action=AuditAction.SCAN_COMPLETED.value,
                result="SUCCESS",
                resource_id=event.resource_id,
                correlation_id=event.correlation_id,
                actor=event.actor,
                event_id=event.event_id,
                details={
                    "resources_scanned": [item.resource_id for item in resources],
                    "finding_count": len(findings),
                },
            )
        )
        log_event(
            self._logger,
            "scan_completed",
            resource=event.resource_id,
            findings=len(findings),
            errors=errors,
        )
        return DetectionOutcome(
            event=event,
            resources=resources,
            findings=findings,
            classified=classified,
            errors=errors,
        )

    def _classify(
        self,
        finding: Finding,
        actor: str,
        resource: StorageResource | None = None,
        assessment: Any = None,
        event: StorageEvent | None = None,
    ) -> ClassifiedFinding:
        try:
            transition(finding, FindingStatus.CLASSIFIED)
        except InvalidLifecycleTransition:
            finding.status = FindingStatus.CLASSIFIED
        decision = self._risk.evaluate(finding)
        finding.decision = decision
        if self._fusion is not None:
            decision = self._fuse(finding, actor, resource, assessment, event)
        try:
            transition(finding, status_for_decision(decision))
        except InvalidLifecycleTransition:
            finding.status = status_for_decision(decision)
        self._audit.append(
            build_record(
                action=AuditAction.RISK_EVALUATED.value,
                result=decision.value,
                resource_id=finding.resource_id,
                correlation_id=finding.correlation_id,
                finding=finding,
                actor=actor,
                event_id=finding.event_id,
                details={"decision": decision.value},
            )
        )
        if decision is RiskDecision.AUTO_REMEDIATE:
            self._publisher.publish(finding)
        elif decision is RiskDecision.ALERT_AND_LOG and self._alerter is not None:
            try:
                self._alerter.alert(finding)
            except Exception as exc:  # noqa: BLE001 - alerting must never abort detection
                log_event(self._logger, "alert_failed", error=str(exc), resource=finding.resource_id)
        return ClassifiedFinding(finding=finding, decision=decision)

    def _fuse(
        self,
        finding: Finding,
        actor: str,
        resource: StorageResource | None,
        assessment: Any,
        event: StorageEvent | None,
    ) -> RiskDecision:
        assert self._fusion is not None
        result: FusionResult = self._fusion.evaluate(finding, resource, assessment, event)
        finding.metadata["fusion"] = result.to_dict()
        finding.decision = result.adjusted_decision
        self._audit.append(
            build_record(
                action=AuditAction.FUSION_EVALUATED.value,
                result=result.adjusted_decision.value,
                resource_id=finding.resource_id,
                correlation_id=finding.correlation_id,
                finding=finding,
                actor=actor,
                event_id=finding.event_id,
                details=result.to_dict(),
            )
        )
        return result.adjusted_decision
