"""Azure Blob Storage inspector and remediator.

The cloud calls sit behind ``AzureStorageApi`` so the mapping logic is testable without an Azure subscription;
``aspare.providers.azure.sdk.SdkAzureStorageApi`` is the real implementation over the Azure management SDK.

Mapping into ASPARe's provider-neutral ``StorageResource``:

* Public Access Block  <- account ``allowBlobPublicAccess`` (blocked when it is explicitly ``False``)
* Public ACL grants    <- containers whose ``publicAccess`` is ``blob`` or ``container``
* Encryption           <- always on (Microsoft-managed keys at minimum), reported as AES256
* Versioning           <- blob service ``isVersioningEnabled``
* HTTPS                <- account ``supportsHttpsTrafficOnly`` ("secure transfer required")
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

PUBLIC_URI = sorted(PUBLIC_ACL_URIS)[0]  # normalised "anyone" marker shared by every provider


class AzureStorageApi(Protocol):
    def list_accounts(self) -> list[str]: ...

    def get_account(self, name: str) -> dict[str, Any]: ...

    def update_account(self, name: str, **changes: Any) -> None: ...

    def get_versioning(self, name: str) -> bool: ...

    def set_versioning(self, name: str, enabled: bool) -> None: ...

    def list_containers(self, name: str) -> list[dict[str, Any]]: ...

    def set_container_private(self, name: str, container: str) -> None: ...


class AzureInspector:
    provider = Provider.AZURE
    resource_type = ResourceType.AZURE_STORAGE_ACCOUNT

    def __init__(self, api: AzureStorageApi) -> None:
        self._api = api

    def list_resource_ids(self) -> list[str]:
        return [f"azure://{name}" for name in self._api.list_accounts()]

    def inspect(self, resource_id: str, region: str | None = None) -> StorageResource:
        name = strip_scheme(resource_id)
        errors: list[str] = []
        try:
            account = self._api.get_account(name)
        except Exception as exc:  # noqa: BLE001
            raise FileNotFoundError(f"Azure storage account {name} was not found ({exc})") from exc
        blocked = account.get("allow_blob_public_access") is False
        pab = PublicAccessBlockState(
            block_public_acls=blocked,
            ignore_public_acls=blocked,
            block_public_policy=blocked,
            restrict_public_buckets=blocked,
            present=True,
        )
        try:
            versioning = VersioningState(status="Enabled" if self._api.get_versioning(name) else None, present=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"get_versioning: {exc}")
            versioning = VersioningState(present=False, error=str(exc))
        try:
            grants = tuple(
                AclGrant("Container", PUBLIC_URI, c["name"], "READ")
                for c in self._api.list_containers(name)
                if c.get("public_access") in {"blob", "container"}
            )
            acl = AclState(grants=grants, present=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"list_containers: {exc}")
            acl = AclState(present=False, error=str(exc))
        return StorageResource(
            provider=Provider.AZURE,
            resource_type=ResourceType.AZURE_STORAGE_ACCOUNT,
            resource_id=f"azure://{name}",
            region=str(account.get("location") or region or ""),
            tags=dict(account.get("tags") or {}),
            public_access_block=pab,
            encryption=EncryptionState(enabled=True, algorithm="AES256", present=True),
            versioning=versioning,
            policy=BucketPolicyState(present=False),
            acl=acl,
            ownership=OwnershipState(present=False),
            inspected_at=datetime.now(UTC),
            inspection_errors=tuple(errors),
            https_only=bool(account.get("https_only")),
        )


class AzureRemediator:
    provider = Provider.AZURE
    resource_type = ResourceType.AZURE_STORAGE_ACCOUNT

    def __init__(self, api: AzureStorageApi) -> None:
        self._api = api

    def enable_public_access_block(self, resource_id: str) -> dict[str, Any]:
        self._api.update_account(strip_scheme(resource_id), allow_blob_public_access=False)
        return {"allow_blob_public_access": False}

    def enable_default_encryption(self, resource_id: str, algorithm: str, kms_key_id: str | None) -> dict[str, Any]:
        return {"note": "Azure Storage encrypts all data at rest; nothing to change."}

    def enable_versioning(self, resource_id: str) -> dict[str, Any]:
        self._api.set_versioning(strip_scheme(resource_id), True)
        return {"is_versioning_enabled": True}

    def merge_secure_transport_policy(self, resource_id: str, statement: dict[str, Any]) -> dict[str, Any]:
        self._api.update_account(strip_scheme(resource_id), https_only=True)
        return {"https_only": True}

    def remove_public_acl_grants(self, resource_id: str) -> dict[str, Any]:
        name = strip_scheme(resource_id)
        removed = []
        for container in self._api.list_containers(name):
            if container.get("public_access") in {"blob", "container"}:
                self._api.set_container_private(name, container["name"])
                removed.append(container["name"])
        return {"made_private": removed}

    def get_tags(self, resource_id: str) -> dict[str, str]:
        return dict(self._api.get_account(strip_scheme(resource_id)).get("tags") or {})
