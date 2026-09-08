"""S3_ENABLE_VERSIONING — enable object versioning."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding, RemediationActionResult
from aspare.remediation.actions.s3.common import run_action
from aspare.remediation.safety import SafetyGate


class EnableVersioningAction:
    action_id = "S3_ENABLE_VERSIONING"

    def __init__(
        self, remediator: StorageRemediator, settings: Settings, gate: SafetyGate
    ) -> None:
        self._remediator = remediator
        self._settings = settings
        self._gate = gate

    def supports(self, finding: Finding) -> bool:
        return finding.remediation_action == self.action_id

    def execute(self, finding: Finding) -> RemediationActionResult:
        return run_action(
            self.action_id,
            finding,
            self._remediator,
            self._settings,
            self._gate,
            lambda: self._remediator.enable_versioning(finding.resource_id),
            "Enabled S3 bucket versioning",
        )
