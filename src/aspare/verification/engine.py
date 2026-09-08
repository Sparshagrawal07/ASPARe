"""Post-remediation verification: re-read the resource and re-run the originating rule."""

from __future__ import annotations

from aspare.core.enums import ActionResultStatus, VerificationOutcome
from aspare.core.interfaces import StorageInspector
from aspare.core.models import Finding, RemediationActionResult, VerificationResult
from aspare.detection.engine import DetectionEngine


class VerificationEngine:
    def __init__(self, inspector: StorageInspector, detection: DetectionEngine) -> None:
        self._inspector = inspector
        self._detection = detection

    def verify(self, finding: Finding, action_result: RemediationActionResult) -> VerificationResult:
        before = action_result.before_state or finding.before_state
        if action_result.status in {ActionResultStatus.FAILED, ActionResultStatus.DENIED}:
            return VerificationResult(
                finding_id=finding.finding_id,
                rule_id=finding.rule_id,
                outcome=VerificationOutcome.ACTION_FAILED,
                verified=False,
                message=action_result.message,
                before_state=before,
            )
        if action_result.status in {ActionResultStatus.UNSUPPORTED, ActionResultStatus.SKIPPED}:
            return VerificationResult(
                finding_id=finding.finding_id,
                rule_id=finding.rule_id,
                outcome=VerificationOutcome.UNSUPPORTED,
                verified=False,
                message=action_result.message,
                before_state=before,
            )
        if action_result.status is ActionResultStatus.DRY_RUN:
            return VerificationResult(
                finding_id=finding.finding_id,
                rule_id=finding.rule_id,
                outcome=VerificationOutcome.UNSUPPORTED,
                verified=False,
                message="Dry-run does not mutate resources, so verification cannot confirm remediation",
                before_state=before,
            )
        try:
            resource = self._inspector.inspect(finding.resource_id, finding.region or None)
        except Exception as exc:  # noqa: BLE001
            return VerificationResult(
                finding_id=finding.finding_id,
                rule_id=finding.rule_id,
                outcome=VerificationOutcome.REREAD_FAILED,
                verified=False,
                message=f"Failed to re-read resource: {exc}",
                before_state=before,
            )
        remaining = self._detection.evaluate_rule(finding.rule_id, resource)
        after = resource.snapshot()
        if remaining is not None:
            return VerificationResult(
                finding_id=finding.finding_id,
                rule_id=finding.rule_id,
                outcome=VerificationOutcome.FINDING_PERSISTED,
                verified=False,
                message="Originating detector still reports a finding after remediation",
                before_state=before,
                after_state=after,
                remaining_finding=remaining,
            )
        return VerificationResult(
            finding_id=finding.finding_id,
            rule_id=finding.rule_id,
            outcome=VerificationOutcome.VERIFIED,
            verified=True,
            message="Originating detector no longer reports a finding",
            before_state=before,
            after_state=after,
        )
