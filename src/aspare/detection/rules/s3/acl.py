"""S3_PUBLIC_ACL_EXPOSURE — grants to AllUsers or AuthenticatedUsers."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import Finding, PolicyDefinition, StorageResource
from aspare.detection.normalizer import normalize_finding
from aspare.s3.https_policy import PUBLIC_ACL_URIS


class PublicAclRule:
    def __init__(self, policy: PolicyDefinition) -> None:
        self.policy = policy
        self.rule_id = policy.rule_id
        self.name = policy.title
        self.description = policy.description

    def supports(self, resource: StorageResource) -> bool:
        return resource.resource_type is ResourceType.S3_BUCKET

    def detect(self, resource: StorageResource) -> Finding | None:
        if resource.ownership.acls_disabled():
            return None
        acl = resource.acl
        if acl.error:
            return None
        public_grants = [
            {
                "grantee_type": grant.grantee_type,
                "grantee_uri": grant.grantee_uri,
                "permission": grant.permission,
            }
            for grant in acl.grants
            if grant.grantee_uri in PUBLIC_ACL_URIS
        ]
        if not public_grants:
            return None
        evidence = {
            "object_ownership": resource.ownership.object_ownership,
            "public_grants": public_grants,
        }
        return normalize_finding(resource, self.policy, evidence)
