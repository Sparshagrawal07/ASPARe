"""Google Cloud Storage inspector and remediator.

Mapping into ASPARe's provider-neutral ``StorageResource``:

* Public Access Block  <- public access prevention ``enforced`` (public policy / buckets) and uniform bucket-level
                          access on (ACLs disabled)
* Public ACL grants    <- IAM bindings for ``allUsers`` / ``allAuthenticatedUsers``
* Encryption           <- always on (Google-managed keys at minimum), reported as AES256
* Versioning           <- object versioning
* HTTPS                <- not applicable: GCS has no per-bucket plain-HTTP setting (organisation policy / VPC-SC)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

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
from aspare.providers.routing import strip_scheme
from aspare.s3.https_policy import PUBLIC_ACL_URIS

_ALL_USERS, _AUTH_USERS = sorted(PUBLIC_ACL_URIS)
_PUBLIC_MEMBERS = {"allUsers": _ALL_USERS, "allAuthenticatedUsers": _AUTH_USERS}
_LABEL_CASE = {"asparedemo": "ASPAReDemo", "dataclass": "DataClass", "purpose": "Purpose", "environment": "Environment"}


class GcsApi(Protocol):
    def list_buckets(self) -> list[str]: ...

    def get_bucket(self, name: str) -> dict[str, Any]: ...

    def patch_bucket(self, name: str, **changes: Any) -> None: ...

    def get_iam_bindings(self, name: str) -> list[dict[str, Any]]: ...

    def remove_public_iam_members(self, name: str) -> list[dict[str, Any]]: ...


class GcsInspector:
    provider = Provider.GCP
    resource_type = ResourceType.GCS_BUCKET

    def __init__(self, api: GcsApi) -> None:
        self._api = api

    def list_resource_ids(self) -> list[str]:
        return [f"gcs://{name}" for name in self._api.list_buckets()]

    def inspect(self, resource_id: str, region: str | None = None) -> StorageResource:
        name = strip_scheme(resource_id)
        errors: list[str] = []
        try:
            bucket = self._api.get_bucket(name)
        except Exception as exc:  # noqa: BLE001
            raise FileNotFoundError(f"GCS bucket {name} was not found ({exc})") from exc
        ubla = bool(bucket.get("uniform_bucket_level_access"))
        prevented = bucket.get("public_access_prevention") == "enforced"
        pab = PublicAccessBlockState(
            block_public_acls=ubla,
            ignore_public_acls=ubla,
            block_public_policy=prevented,
            restrict_public_buckets=prevented,
            present=True,
        )
        try:
            grants = tuple(
                AclGrant("IAMBinding", _PUBLIC_MEMBERS[member], member, binding.get("role", ""))
                for binding in self._api.get_iam_bindings(name)
                for member in binding.get("members", [])
                if member in _PUBLIC_MEMBERS
            )
            acl = AclState(grants=grants, present=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"get_iam_bindings: {exc}")
            acl = AclState(present=False, error=str(exc))
        return StorageResource(
            provider=Provider.GCP,
            resource_type=ResourceType.GCS_BUCKET,
            resource_id=f"gcs://{name}",
            region=str(bucket.get("location") or region or "").lower(),
            tags=_normalise_labels(bucket.get("labels") or {}),
            public_access_block=pab,
            encryption=EncryptionState(
                enabled=True, algorithm="AES256", kms_key_id=bucket.get("default_kms_key"), present=True
            ),
            versioning=VersioningState(status="Enabled" if bucket.get("versioning_enabled") else None, present=True),
            policy=BucketPolicyState(present=False),
            acl=acl,
            ownership=OwnershipState(present=False),
            inspected_at=datetime.now(UTC),
            inspection_errors=tuple(errors),
            https_only=None,
        )


class GcsRemediator:
    provider = Provider.GCP
    resource_type = ResourceType.GCS_BUCKET

    def __init__(self, api: GcsApi) -> None:
        self._api = api

    def enable_public_access_block(self, resource_id: str) -> dict[str, Any]:
        self._api.patch_bucket(
            strip_scheme(resource_id), public_access_prevention="enforced", uniform_bucket_level_access=True
        )
        return {"public_access_prevention": "enforced", "uniform_bucket_level_access": True}

    def enable_default_encryption(self, resource_id: str, algorithm: str, kms_key_id: str | None) -> dict[str, Any]:
        return {"note": "Cloud Storage encrypts all data at rest; nothing to change."}

    def enable_versioning(self, resource_id: str) -> dict[str, Any]:
        self._api.patch_bucket(strip_scheme(resource_id), versioning_enabled=True)
        return {"versioning_enabled": True}

    def merge_secure_transport_policy(self, resource_id: str, statement: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("GCS has no per-bucket secure-transport setting")

    def remove_public_acl_grants(self, resource_id: str) -> dict[str, Any]:
        return {"removed": self._api.remove_public_iam_members(strip_scheme(resource_id))}

    def get_tags(self, resource_id: str) -> dict[str, str]:
        return _normalise_labels(self._api.get_bucket(strip_scheme(resource_id)).get("labels") or {})


def _normalise_labels(labels: dict[str, str]) -> dict[str, str]:
    """GCS label keys are lowercase; map the ones ASPARe uses back to their canonical names."""
    return {_LABEL_CASE.get(key, key): value for key, value in labels.items()}
