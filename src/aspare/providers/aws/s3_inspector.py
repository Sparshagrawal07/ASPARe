"""Read-only Amazon S3 inspector that produces StorageResource snapshots."""

from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from aspare.core.enums import Provider, ResourceType
from aspare.core.models import (
    AclGrant,
    AclState,
    BucketPolicyState,
    EncryptionState,
    OwnershipState,
    PublicAccessBlockState,
    StorageResource,
    VersioningState,
)
from aspare.core.timeutil import utcnow
from aspare.providers.aws.client import s3_client

_ABSENT_CODES = {
    "NoSuchPublicAccessBlockConfiguration",
    "NoSuchBucketPolicy",
    "NoSuchEncryptionConfiguration",
    "ServerSideEncryptionConfigurationNotFoundError",
    "OwnershipControlsNotFoundError",
    "NoSuchLifecycleConfiguration",
}


class S3Inspector:
    provider = Provider.AWS
    resource_type = ResourceType.S3_BUCKET

    def __init__(self, client: Any | None = None, region: str = "us-east-1") -> None:
        self._client = client or s3_client(region)
        self._region = region

    def inspect(self, resource_id: str, region: str | None = None) -> StorageResource:
        try:
            self._client.head_bucket(Bucket=resource_id)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            raise FileNotFoundError(f"S3 bucket {resource_id} was not found ({code})") from exc
        errors: list[str] = []
        pab = self._public_access_block(resource_id, errors)
        encryption = self._encryption(resource_id, errors)
        versioning = self._versioning(resource_id, errors)
        policy = self._policy(resource_id, errors)
        acl = self._acl(resource_id, errors)
        ownership = self._ownership(resource_id, errors)
        tags = self._tags(resource_id, errors)
        resolved_region = region or self._location(resource_id, errors) or self._region
        return StorageResource(
            provider=Provider.AWS,
            resource_type=ResourceType.S3_BUCKET,
            resource_id=resource_id,
            region=resolved_region,
            tags=tags,
            public_access_block=pab,
            encryption=encryption,
            versioning=versioning,
            policy=policy,
            acl=acl,
            ownership=ownership,
            inspected_at=utcnow(),
            inspection_errors=tuple(errors),
        )

    def list_resource_ids(self) -> list[str]:
        response = self._client.list_buckets()
        return [bucket["Name"] for bucket in response.get("Buckets", [])]

    def _call(self, method: str, errors: list[str], **kwargs: Any) -> dict[str, Any] | None:
        try:
            return getattr(self._client, method)(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in _ABSENT_CODES:
                return None
            errors.append(f"{method}: {code}: {exc.response.get('Error', {}).get('Message', str(exc))}")
            return None
        except (BotoCoreError, Exception) as exc:  # noqa: BLE001 - inspector must not abort the scan
            errors.append(f"{method}: {exc}")
            return None

    def _public_access_block(self, bucket: str, errors: list[str]) -> PublicAccessBlockState:
        response = self._call("get_public_access_block", errors, Bucket=bucket)
        if response is None and not any(item.startswith("get_public_access_block:") for item in errors):
            return PublicAccessBlockState(present=False)
        if response is None:
            return PublicAccessBlockState(present=False, error=errors[-1] if errors else "unavailable")
        cfg = response.get("PublicAccessBlockConfiguration") or {}
        return PublicAccessBlockState(
            block_public_acls=cfg.get("BlockPublicAcls"),
            ignore_public_acls=cfg.get("IgnorePublicAcls"),
            block_public_policy=cfg.get("BlockPublicPolicy"),
            restrict_public_buckets=cfg.get("RestrictPublicBuckets"),
            present=True,
        )

    def _encryption(self, bucket: str, errors: list[str]) -> EncryptionState:
        response = self._call("get_bucket_encryption", errors, Bucket=bucket)
        if response is None and not any(item.startswith("get_bucket_encryption:") for item in errors):
            return EncryptionState(present=False, enabled=False)
        if response is None:
            return EncryptionState(present=False, enabled=False, error=errors[-1] if errors else "unavailable")
        rules = (response.get("ServerSideEncryptionConfiguration") or {}).get("Rules") or []
        if not rules:
            return EncryptionState(present=True, enabled=False)
        apply = (rules[0].get("ApplyServerSideEncryptionByDefault") or {})
        algorithm = apply.get("SSEAlgorithm")
        return EncryptionState(
            enabled=bool(algorithm),
            algorithm=algorithm,
            kms_key_id=apply.get("KMSMasterKeyID"),
            bucket_key_enabled=rules[0].get("BucketKeyEnabled"),
            present=True,
        )

    def _versioning(self, bucket: str, errors: list[str]) -> VersioningState:
        response = self._call("get_bucket_versioning", errors, Bucket=bucket)
        if response is None:
            return VersioningState(present=False, error=errors[-1] if errors else "unavailable")
        status = response.get("Status")
        return VersioningState(status=status, present=True)

    def _policy(self, bucket: str, errors: list[str]) -> BucketPolicyState:
        response = self._call("get_bucket_policy", errors, Bucket=bucket)
        if response is None and not any(item.startswith("get_bucket_policy:") for item in errors):
            return BucketPolicyState(present=False)
        if response is None:
            return BucketPolicyState(present=False, error=errors[-1] if errors else "unavailable")
        raw = response.get("Policy")
        try:
            document = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as exc:
            errors.append(f"get_bucket_policy: invalid JSON: {exc}")
            return BucketPolicyState(present=True, error=str(exc))
        return BucketPolicyState(document=document, present=True)

    def _acl(self, bucket: str, errors: list[str]) -> AclState:
        response = self._call("get_bucket_acl", errors, Bucket=bucket)
        if response is None:
            return AclState(present=False, error=errors[-1] if errors else "unavailable")
        grants = []
        for grant in response.get("Grants") or []:
            grantee = grant.get("Grantee") or {}
            grants.append(
                AclGrant(
                    grantee_type=str(grantee.get("Type") or ""),
                    grantee_uri=grantee.get("URI"),
                    grantee_id=grantee.get("ID"),
                    permission=str(grant.get("Permission") or ""),
                )
            )
        owner = (response.get("Owner") or {}).get("ID")
        return AclState(owner_id=owner, grants=tuple(grants), present=True)

    def _ownership(self, bucket: str, errors: list[str]) -> OwnershipState:
        response = self._call("get_bucket_ownership_controls", errors, Bucket=bucket)
        if response is None and not any(item.startswith("get_bucket_ownership_controls:") for item in errors):
            return OwnershipState(present=False)
        if response is None:
            return OwnershipState(present=False, error=errors[-1] if errors else "unavailable")
        rules = (response.get("OwnershipControls") or {}).get("Rules") or []
        ownership = rules[0].get("ObjectOwnership") if rules else None
        return OwnershipState(object_ownership=ownership, present=True)

    def _tags(self, bucket: str, errors: list[str]) -> dict[str, str]:
        response = self._call("get_bucket_tagging", errors, Bucket=bucket)
        if response is None:
            return {}
        return {tag["Key"]: tag["Value"] for tag in response.get("TagSet") or []}

    def _location(self, bucket: str, errors: list[str]) -> str | None:
        response = self._call("get_bucket_location", errors, Bucket=bucket)
        if not response:
            return None
        constraint = response.get("LocationConstraint")
        if not constraint:
            return "us-east-1"
        return str(constraint)
