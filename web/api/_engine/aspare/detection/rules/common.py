"""Shared helpers for provider-neutral detection rules."""

from __future__ import annotations

from aspare.core.enums import ResourceType
from aspare.core.models import StorageResource

STORAGE_TYPES = frozenset({ResourceType.S3_BUCKET, ResourceType.AZURE_STORAGE_ACCOUNT, ResourceType.GCS_BUCKET})


def is_storage(resource: StorageResource) -> bool:
    return resource.resource_type in STORAGE_TYPES
