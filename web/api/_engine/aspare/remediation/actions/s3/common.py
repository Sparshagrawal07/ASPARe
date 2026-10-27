"""Shared execute wrapper for S3 remediation actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aspare.config.settings import Settings
from aspare.core.enums import ActionResultStatus
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding, RemediationActionResult
from aspare.remediation.safety import SafetyDenied, SafetyGate


def run_action(
    action_id: str,
    finding: Finding,
    remediator: StorageRemediator,
    settings: Settings,
    gate: SafetyGate,
    mutator: Callable[[], dict[str, Any]],
    success_message: str,
) -> RemediationActionResult:
    before = dict(finding.before_state)
    try:
        gate.assert_allowed(finding, remediator)
    except SafetyDenied as exc:
        return RemediationActionResult(
            action_id=action_id,
            finding_id=finding.finding_id,
            status=ActionResultStatus.DENIED,
            message=str(exc),
            before_state=before,
        )
    if settings.dry_run:
        return RemediationActionResult(
            action_id=action_id,
            finding_id=finding.finding_id,
            status=ActionResultStatus.DRY_RUN,
            message=f"Dry-run: would execute {action_id}",
            before_state=before,
            dry_run=True,
        )
    try:
        after = mutator()
    except Exception as exc:  # noqa: BLE001
        return RemediationActionResult(
            action_id=action_id,
            finding_id=finding.finding_id,
            status=ActionResultStatus.FAILED,
            message=str(exc),
            before_state=before,
        )
    return RemediationActionResult(
        action_id=action_id,
        finding_id=finding.finding_id,
        status=ActionResultStatus.SUCCESS,
        message=success_message,
        before_state=before,
        after_state=after if isinstance(after, dict) else {"result": after},
    )
