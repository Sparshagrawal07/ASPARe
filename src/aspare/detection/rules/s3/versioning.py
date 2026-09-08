"""S3_VERSIONING_DISABLED — absent or suspended object versioning."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import Finding, PolicyDefinition, StorageResource
from aspare.detection.normalizer import normalize_finding


class VersioningDisabledRule:
    def __init__(self, policy: PolicyDefinition) -> None:
        self.policy = policy
        self.rule_id = policy.rule_id
        self.name = policy.title
        self.description = policy.description

    def supports(self, resource: StorageResource) -> bool:
        return resource.resource_type is ResourceType.S3_BUCKET

    def detect(self, resource: StorageResource) -> Finding | None:
        versioning = resource.versioning
        if versioning.error:
            return None
        if versioning.is_enabled():
            return None
        evidence = {"present": versioning.present, "status": versioning.status}
        return normalize_finding(resource, self.policy, evidence)
