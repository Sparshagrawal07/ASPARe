"""S3_BLOCK_PUBLIC_ACCESS — enable all four Public Access Block flags."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding, RemediationActionResult
from aspare.remediation.actions.s3.common import run_action
from aspare.remediation.safety import SafetyGate


class BlockPublicAccessAction:
    action_id = "S3_BLOCK_PUBLIC_ACCESS"

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
            lambda: self._remediator.enable_public_access_block(finding.resource_id),
            "Enabled all S3 Public Access Block controls",
        )
