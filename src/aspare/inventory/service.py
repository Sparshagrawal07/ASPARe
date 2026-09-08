"""Storage inventory service: resolve events into StorageResource snapshots."""

from __future__ import annotations

from aspare.config.settings import Settings
from aspare.core.enums import ResourceType
from aspare.core.models import StorageEvent, StorageResource
from aspare.providers.registry import ProviderRegistry


class InventoryService:
    def __init__(self, providers: ProviderRegistry, settings: Settings) -> None:
        self._providers = providers
        self._settings = settings

    def resources_for(self, event: StorageEvent) -> list[StorageResource]:
        inspector = self._providers.inspector(event.provider, event.resource_type)
        if event.resource_id == "*":
            ids = inspector.list_resource_ids()
            if self._settings.allowed_buckets:
                ids = [item for item in ids if item in self._settings.allowed_buckets]
            return [inspector.inspect(item, event.region) for item in ids]
        if event.resource_type is not ResourceType.S3_BUCKET:
            return []
        if self._settings.allowed_buckets and event.resource_id not in self._settings.allowed_buckets:
            return []
        return [inspector.inspect(event.resource_id, event.region)]
