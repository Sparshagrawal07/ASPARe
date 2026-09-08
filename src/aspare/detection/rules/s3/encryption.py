"""S3_ENCRYPTION_DISABLED — missing or noncompliant default encryption."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import Finding, PolicyDefinition, StorageResource
from aspare.detection.normalizer import normalize_finding


class EncryptionDisabledRule:
    def __init__(
        self,
        policy: PolicyDefinition,
        accepted_algorithms: tuple[str, ...] = ("AES256", "aws:kms", "aws:kms:dsse"),
    ) -> None:
        self.policy = policy
        self.rule_id = policy.rule_id
        self.name = policy.title
        self.description = policy.description
        self.accepted_algorithms = tuple(item.upper() for item in accepted_algorithms)

    def supports(self, resource: StorageResource) -> bool:
        return resource.resource_type is ResourceType.S3_BUCKET

    def detect(self, resource: StorageResource) -> Finding | None:
        encryption = resource.encryption
        if encryption.error:
            return None
        algorithm = (encryption.algorithm or "").upper()
        compliant = encryption.present and encryption.enabled and algorithm in self.accepted_algorithms
        if compliant:
            return None
        evidence = {
            "present": encryption.present,
            "enabled": encryption.enabled,
            "algorithm": encryption.algorithm,
            "accepted_algorithms": list(self.accepted_algorithms),
            "baseline_encryption_note": (
                "Modern Amazon S3 may encrypt new objects even when GetBucketEncryption "
                "reports no explicit bucket configuration. ASPARe still requires an explicit "
                "default encryption configuration as the policy control."
            ),
        }
        return normalize_finding(resource, self.policy, evidence)
