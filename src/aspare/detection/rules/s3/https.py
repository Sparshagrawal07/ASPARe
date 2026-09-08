"""S3_HTTPS_ENFORCEMENT_MISSING — no Deny for aws:SecureTransport=false."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import Finding, PolicyDefinition, StorageResource
from aspare.detection.normalizer import normalize_finding
from aspare.s3.https_policy import has_secure_transport_deny


class HttpsEnforcementRule:
    def __init__(self, policy: PolicyDefinition) -> None:
        self.policy = policy
        self.rule_id = policy.rule_id
        self.name = policy.title
        self.description = policy.description

    def supports(self, resource: StorageResource) -> bool:
        return resource.resource_type is ResourceType.S3_BUCKET

    def detect(self, resource: StorageResource) -> Finding | None:
        policy_state = resource.policy
        if policy_state.error:
            return None
        if has_secure_transport_deny(policy_state.document, resource.resource_id):
            return None
        evidence = {
            "policy_present": policy_state.present,
            "has_secure_transport_deny": False,
        }
        return normalize_finding(resource, self.policy, evidence)
