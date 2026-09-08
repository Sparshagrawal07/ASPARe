"""Write-only Amazon S3 remediator. Detectors never import this module."""

from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import ClientError

from aspare.core.enums import Provider, ResourceType
from aspare.providers.aws.client import s3_client
from aspare.s3.https_policy import HTTPS_SID, secure_transport_statement, statements_of

PUBLIC_URIS = {
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
}

FULL_PUBLIC_ACCESS_BLOCK = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


class S3Remediator:
    provider = Provider.AWS
    resource_type = ResourceType.S3_BUCKET

    def __init__(self, client: Any | None = None, region: str = "us-east-1") -> None:
        self._client = client or s3_client(region)

    def enable_public_access_block(self, resource_id: str) -> dict[str, Any]:
        self._client.put_public_access_block(
            Bucket=resource_id, PublicAccessBlockConfiguration=FULL_PUBLIC_ACCESS_BLOCK
        )
        return dict(FULL_PUBLIC_ACCESS_BLOCK)

    def enable_default_encryption(
        self, resource_id: str, algorithm: str, kms_key_id: str | None
    ) -> dict[str, Any]:
        rule: dict[str, Any] = {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": algorithm}}
        if kms_key_id and algorithm.lower().startswith("aws:kms"):
            rule["ApplyServerSideEncryptionByDefault"]["KMSMasterKeyID"] = kms_key_id
            rule["BucketKeyEnabled"] = True
        self._client.put_bucket_encryption(
            Bucket=resource_id, ServerSideEncryptionConfiguration={"Rules": [rule]}
        )
        return rule

    def enable_versioning(self, resource_id: str) -> dict[str, Any]:
        self._client.put_bucket_versioning(
            Bucket=resource_id, VersioningConfiguration={"Status": "Enabled"}
        )
        return {"Status": "Enabled"}

    def merge_secure_transport_policy(
        self, resource_id: str, statement: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        statement = statement or secure_transport_statement(resource_id)
        document = self._load_policy(resource_id)
        existing = statements_of(document)
        replaced = False
        merged: list[dict[str, Any]] = []
        for item in existing:
            if item.get("Sid") == HTTPS_SID:
                merged.append(statement)
                replaced = True
            else:
                merged.append(item)
        if not replaced:
            merged.append(statement)
        document = {
            "Version": document.get("Version") or "2012-10-17",
            "Statement": merged,
        }
        self._client.put_bucket_policy(Bucket=resource_id, Policy=json.dumps(document))
        return document

    def remove_public_acl_grants(self, resource_id: str) -> dict[str, Any]:
        acl = self._client.get_bucket_acl(Bucket=resource_id)
        owner = acl.get("Owner") or {}
        kept = []
        removed = []
        for grant in acl.get("Grants") or []:
            uri = (grant.get("Grantee") or {}).get("URI")
            if uri in PUBLIC_URIS:
                removed.append(grant)
                continue
            kept.append(grant)
        access_control_policy = {"Owner": owner, "Grants": kept}
        self._client.put_bucket_acl(Bucket=resource_id, AccessControlPolicy=access_control_policy)
        return {"removed": removed, "remaining": kept}

    def get_tags(self, resource_id: str) -> dict[str, str]:
        try:
            response = self._client.get_bucket_tagging(Bucket=resource_id)
        except ClientError:
            return {}
        return {tag["Key"]: tag["Value"] for tag in response.get("TagSet") or []}

    def _load_policy(self, resource_id: str) -> dict[str, Any]:
        try:
            raw = self._client.get_bucket_policy(Bucket=resource_id)["Policy"]
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "NoSuchBucketPolicy":
                return {"Version": "2012-10-17", "Statement": []}
            raise
        document = json.loads(raw) if isinstance(raw, str) else raw
        return document or {"Version": "2012-10-17", "Statement": []}
