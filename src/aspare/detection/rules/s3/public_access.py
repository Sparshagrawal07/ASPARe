"""S3_PUBLIC_ACCESS — incomplete bucket Public Access Block controls."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import Finding, PolicyDefinition, StorageResource
from aspare.detection.normalizer import normalize_finding


class PublicAccessRule:
    def __init__(self, policy: PolicyDefinition) -> None:
        self.policy = policy
        self.rule_id = policy.rule_id
        self.name = policy.title
        self.description = policy.description

    def supports(self, resource: StorageResource) -> bool:
        return resource.resource_type is ResourceType.S3_BUCKET

    def detect(self, resource: StorageResource) -> Finding | None:
        pab = resource.public_access_block
        if pab.error:
            return None
        if pab.all_blocked():
            return None
        evidence = {
            "present": pab.present,
            "block_public_acls": pab.block_public_acls,
            "ignore_public_acls": pab.ignore_public_acls,
            "block_public_policy": pab.block_public_policy,
            "restrict_public_buckets": pab.restrict_public_buckets,
        }
        return normalize_finding(resource, self.policy, evidence)
