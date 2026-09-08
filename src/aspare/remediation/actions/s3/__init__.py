"""S3 remediation actions."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import RemediationAction, StorageRemediator
from aspare.remediation.actions.s3.acl import RemovePublicAclAction
from aspare.remediation.actions.s3.encryption import EnableDefaultEncryptionAction
from aspare.remediation.actions.s3.https import EnforceHttpsAction
from aspare.remediation.actions.s3.public_access import BlockPublicAccessAction
from aspare.remediation.actions.s3.versioning import EnableVersioningAction
from aspare.remediation.safety import SafetyGate


def default_s3_actions(
    remediator: StorageRemediator, settings: Settings, gate: SafetyGate | None = None
) -> list[RemediationAction]:
    gate = gate or SafetyGate(settings)
    return [
        BlockPublicAccessAction(remediator, settings, gate),
        EnableDefaultEncryptionAction(remediator, settings, gate),
        EnableVersioningAction(remediator, settings, gate),
        EnforceHttpsAction(remediator, settings, gate),
        RemovePublicAclAction(remediator, settings, gate),
    ]
