"""S3_REMOVE_PUBLIC_ACL — drop AllUsers/AuthenticatedUsers grants only."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding, RemediationActionResult
from aspare.remediation.actions.s3.common import run_action
from aspare.remediation.safety import SafetyGate


class RemovePublicAclAction:
    action_id = "S3_REMOVE_PUBLIC_ACL"

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
            lambda: self._remediator.remove_public_acl_grants(finding.resource_id),
            "Removed public ACL grants while preserving owner and private grants",
        )
