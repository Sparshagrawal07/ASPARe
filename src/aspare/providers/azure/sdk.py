"""Real Azure implementation of ``AzureStorageApi`` over ``azure-mgmt-storage`` (install ``aspare[azure]``).

Not exercised in CI (needs a subscription); the mapping logic above it is covered with a fake API. Required RBAC on
the resource group: Reader for detection, plus "Storage Account Contributor" for remediation.
"""

from __future__ import annotations

from typing import Any


class SdkAzureStorageApi:
    def __init__(self, subscription_id: str, resource_group: str, credential: Any | None = None) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.storage import StorageManagementClient

        self._rg = resource_group
        self._client = StorageManagementClient(credential or DefaultAzureCredential(), subscription_id)

    def list_accounts(self) -> list[str]:
        return [a.name for a in self._client.storage_accounts.list_by_resource_group(self._rg)]

    def get_account(self, name: str) -> dict[str, Any]:
        a = self._client.storage_accounts.get_properties(self._rg, name)
        return {
            "location": a.location,
            "tags": a.tags or {},
            "allow_blob_public_access": a.allow_blob_public_access,
            "https_only": a.enable_https_traffic_only,
        }

    def update_account(self, name: str, **changes: Any) -> None:
        from azure.mgmt.storage.models import StorageAccountUpdateParameters

        params = StorageAccountUpdateParameters(
            allow_blob_public_access=changes.get("allow_blob_public_access"),
            enable_https_traffic_only=changes.get("https_only"),
        )
        self._client.storage_accounts.update(self._rg, name, params)

    def get_versioning(self, name: str) -> bool:
        props = self._client.blob_services.get_service_properties(self._rg, name)
        return bool(props.is_versioning_enabled)

    def set_versioning(self, name: str, enabled: bool) -> None:
        from azure.mgmt.storage.models import BlobServiceProperties

        self._client.blob_services.set_service_properties(
            self._rg, name, BlobServiceProperties(is_versioning_enabled=enabled)
        )

    def list_containers(self, name: str) -> list[dict[str, Any]]:
        return [
            {"name": c.name, "public_access": str(c.public_access or "none").lower()}
            for c in self._client.blob_containers.list(self._rg, name)
        ]

    def set_container_private(self, name: str, container: str) -> None:
        from azure.mgmt.storage.models import BlobContainer

        self._client.blob_containers.update(self._rg, name, container, BlobContainer(public_access="None"))
