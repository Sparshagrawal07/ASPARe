"""Remediation workflow: action → verification → audit → lifecycle update."""

from __future__ import annotations

from aspare.audit.repository import build_record
from aspare.core.enums import AuditAction, FindingStatus, VerificationOutcome
from aspare.core.interfaces import AuditRepository
from aspare.core.lifecycle import InvalidLifecycleTransition, transition
from aspare.core.models import Finding, RemediationOutcome
from aspare.logging import get_logger, log_event
from aspare.remediation.engine import RemediationEngine
from aspare.verification.engine import VerificationEngine


class RemediationWorkflow:
    def __init__(
        self,
        remediation: RemediationEngine,
        verification: VerificationEngine,
        audit: AuditRepository,
    ) -> None:
        self._remediation = remediation
        self._verification = verification
        self._audit = audit
        self._logger = get_logger("aspare.remediation")

    def run(self, finding: Finding) -> RemediationOutcome:
        self._safe_transition(finding, FindingStatus.PENDING_REMEDIATION)
        self._safe_transition(finding, FindingStatus.REMEDIATING)
        self._audit.append(
            build_record(
                action=AuditAction.REMEDIATION_STARTED.value,
                result="STARTED",
                resource_id=finding.resource_id,
                correlation_id=finding.correlation_id,
                finding=finding,
            )
        )
        action_result = self._remediation.execute(finding)
        self._audit.append(
            build_record(
                action=AuditAction.REMEDIATION_EXECUTED.value,
                result=action_result.status.value,
                resource_id=finding.resource_id,
                correlation_id=finding.correlation_id,
                finding=finding,
                before_state=action_result.before_state,
                after_state=action_result.after_state,
                details={"message": action_result.message, "action_id": action_result.action_id},
            )
        )
        if not action_result.succeeded():
            self._safe_transition(finding, FindingStatus.REMEDIATION_FAILED)
            verification = self._verification.verify(finding, action_result)
            return self._finish(finding, action_result, verification)

        self._safe_transition(finding, FindingStatus.VERIFYING)
        verification = self._verification.verify(finding, action_result)
        if verification.outcome is VerificationOutcome.VERIFIED:
            self._safe_transition(finding, FindingStatus.REMEDIATED)
        else:
            self._safe_transition(finding, FindingStatus.REMEDIATION_FAILED)
        return self._finish(finding, action_result, verification)

    def _finish(self, finding, action_result, verification) -> RemediationOutcome:
        self._audit.append(
            build_record(
                action=AuditAction.VERIFICATION_COMPLETED.value,
                result=verification.outcome.value,
                resource_id=finding.resource_id,
                correlation_id=finding.correlation_id,
                finding=finding,
                verified=verification.verified,
                before_state=verification.before_state,
                after_state=verification.after_state,
                details={"message": verification.message},
            )
        )
        log_event(
            self._logger,
            "remediation_complete",
            finding_id=finding.finding_id,
            action=action_result.action_id,
            verified=verification.verified,
            status=finding.status.value,
        )
        return RemediationOutcome(
            finding=finding,
            action_result=action_result,
            verification=verification,
            status=finding.status,
        )

    @staticmethod
    def _safe_transition(finding: Finding, target: FindingStatus) -> None:
        try:
            transition(finding, target)
        except InvalidLifecycleTransition:
            finding.status = target
