"""S3_ENFORCE_HTTPS — merge a reviewed secure-transport Deny statement."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding, RemediationActionResult
from aspare.remediation.actions.s3.common import run_action
from aspare.remediation.safety import SafetyGate
from aspare.s3.https_policy import HTTPS_SID, secure_transport_statement


class EnforceHttpsAction:
    action_id = "S3_ENFORCE_HTTPS"

    def __init__(
        self, remediator: StorageRemediator, settings: Settings, gate: SafetyGate
    ) -> None:
        self._remediator = remediator
        self._settings = settings
        self._gate = gate

    def supports(self, finding: Finding) -> bool:
        return finding.remediation_action == self.action_id

    def execute(self, finding: Finding) -> RemediationActionResult:
        statement = secure_transport_statement(finding.resource_id)
        return run_action(
            self.action_id,
            finding,
            self._remediator,
            self._settings,
            self._gate,
            lambda: self._remediator.merge_secure_transport_policy(
                finding.resource_id, statement
            ),
            f"Merged reviewed bucket-policy statement {HTTPS_SID}",
        )
