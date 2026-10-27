"""Safety gate for write operations against S3."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import StorageRemediator
from aspare.core.models import Finding


class SafetyDenied(PermissionError):
    pass


class SafetyGate:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def assert_allowed(self, finding: Finding, remediator: StorageRemediator) -> None:
        tags = remediator.get_tags(finding.resource_id)
        if not self.settings.is_bucket_allowed(finding.resource_id, tags):
            raise SafetyDenied(
                f"Refusing to mutate {finding.resource_id}: bucket is outside the ASPARe "
                "allowlist or is missing the required ASPAReDemo=true tag"
            )
