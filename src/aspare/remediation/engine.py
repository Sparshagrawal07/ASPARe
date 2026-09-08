"""Remediation action registry. Actions mutate AWS only through StorageRemediator."""

from __future__ import annotations

from aspare.core.enums import ActionResultStatus
from aspare.core.interfaces import RemediationAction
from aspare.core.models import Finding, RemediationActionResult


class RemediationEngine:
    def __init__(self, actions: list[RemediationAction]) -> None:
        self._actions = list(actions)
        self._by_id = {action.action_id: action for action in actions}

    def select(self, finding: Finding) -> RemediationAction | None:
        action = self._by_id.get(finding.remediation_action)
        if action and action.supports(finding):
            return action
        for candidate in self._actions:
            if candidate.supports(finding):
                return candidate
        return None

    def execute(self, finding: Finding) -> RemediationActionResult:
        action = self.select(finding)
        if action is None:
            return RemediationActionResult(
                action_id=finding.remediation_action or "unknown",
                finding_id=finding.finding_id,
                status=ActionResultStatus.UNSUPPORTED,
                message=f"No remediation action registered for {finding.rule_id}",
                before_state=finding.before_state,
            )
        try:
            return action.execute(finding)
        except Exception as exc:  # noqa: BLE001 - convert to structured action failure
            return RemediationActionResult(
                action_id=action.action_id,
                finding_id=finding.finding_id,
                status=ActionResultStatus.FAILED,
                message=str(exc),
                before_state=finding.before_state,
            )
