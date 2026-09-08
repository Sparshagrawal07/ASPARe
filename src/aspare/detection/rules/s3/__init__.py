"""S3 detection rules. Each rule returns a Finding or None and never mutates AWS."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.interfaces import DetectionRule
from aspare.detection.rules.s3.acl import PublicAclRule
from aspare.detection.rules.s3.encryption import EncryptionDisabledRule
from aspare.detection.rules.s3.https import HttpsEnforcementRule
from aspare.detection.rules.s3.public_access import PublicAccessRule
from aspare.detection.rules.s3.versioning import VersioningDisabledRule
from aspare.policy.registry import PolicyRegistry


def default_s3_rules(registry: PolicyRegistry, settings: Settings | None = None) -> list[DetectionRule]:
    settings = settings or Settings()
    return [
        PublicAccessRule(registry.by_rule("S3_PUBLIC_ACCESS")),
        EncryptionDisabledRule(
            registry.by_rule("S3_ENCRYPTION_DISABLED"),
            accepted_algorithms=settings.accepted_encryption_algorithms,
        ),
        VersioningDisabledRule(registry.by_rule("S3_VERSIONING_DISABLED")),
        HttpsEnforcementRule(registry.by_rule("S3_HTTPS_ENFORCEMENT_MISSING")),
        PublicAclRule(registry.by_rule("S3_PUBLIC_ACL_EXPOSURE")),
    ]
