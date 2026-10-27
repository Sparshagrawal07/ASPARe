"""Route storage calls to the right cloud by resource-id scheme.

AWS buckets keep their plain name; other clouds use a scheme prefix so one finding stream, one safety gate and one
verification engine can serve every provider: ``gcs://bucket`` and ``azure://storage-account``.
"""

from __future__ import annotations

from typing import Any

from aspare.core.enums import Provider, ResourceType
from aspare.core.interfaces import StorageInspector, StorageRemediator
from aspare.core.models import StorageResource

_PREFIXES = {
    "azure://": (Provider.AZURE, ResourceType.AZURE_STORAGE_ACCOUNT),
    "gcs://": (Provider.GCP, ResourceType.GCS_BUCKET),
}


def identity_for(resource_id: str) -> tuple[Provider, ResourceType]:
    for prefix, identity in _PREFIXES.items():
        if resource_id.startswith(prefix):
            return identity
    return Provider.AWS, ResourceType.S3_BUCKET


def strip_scheme(resource_id: str) -> str:
    for prefix in _PREFIXES:
        if resource_id.startswith(prefix):
            return resource_id[len(prefix) :]
    return resource_id


class SimpleProvider:
    def __init__(
        self,
        provider: Provider,
        resource_type: ResourceType,
        inspector: StorageInspector,
        remediator: StorageRemediator,
    ) -> None:
        self.provider = provider
        self._resource_type = resource_type
        self._inspector = inspector
        self._remediator = remediator

    def inspector(self, resource_type: ResourceType) -> StorageInspector:
        return self._inspector

    def remediator(self, resource_type: ResourceType) -> StorageRemediator:
        return self._remediator


class RoutingInspector:
    provider = Provider.AWS
    resource_type = ResourceType.S3_BUCKET

    def __init__(self, inspectors: dict[Provider, StorageInspector]) -> None:
        self._inspectors = inspectors

    def inspect(self, resource_id: str, region: str | None = None) -> StorageResource:
        provider, _ = identity_for(resource_id)
        return self._inspectors[provider].inspect(resource_id, region)

    def list_resource_ids(self) -> list[str]:
        return self._inspectors[Provider.AWS].list_resource_ids()


class RoutingRemediator:
    provider = Provider.AWS
    resource_type = ResourceType.S3_BUCKET

    def __init__(self, remediators: dict[Provider, StorageRemediator]) -> None:
        self._remediators = remediators

    def _for(self, resource_id: str) -> StorageRemediator:
        return self._remediators[identity_for(resource_id)[0]]

    def enable_public_access_block(self, resource_id: str) -> dict[str, Any]:
        return self._for(resource_id).enable_public_access_block(resource_id)

    def enable_default_encryption(self, resource_id: str, algorithm: str, kms_key_id: str | None) -> dict[str, Any]:
        return self._for(resource_id).enable_default_encryption(resource_id, algorithm, kms_key_id)

    def enable_versioning(self, resource_id: str) -> dict[str, Any]:
        return self._for(resource_id).enable_versioning(resource_id)

    def merge_secure_transport_policy(self, resource_id: str, statement: dict[str, Any]) -> dict[str, Any]:
        return self._for(resource_id).merge_secure_transport_policy(resource_id, statement)

    def remove_public_acl_grants(self, resource_id: str) -> dict[str, Any]:
        return self._for(resource_id).remove_public_acl_grants(resource_id)

    def get_tags(self, resource_id: str) -> dict[str, str]:
        return self._for(resource_id).get_tags(resource_id)
