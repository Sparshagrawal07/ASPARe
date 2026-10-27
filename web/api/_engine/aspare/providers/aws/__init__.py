"""AWS S3 provider."""

from aspare.core.enums import Provider, ResourceType
from aspare.core.interfaces import StorageInspector, StorageRemediator
from aspare.providers.aws.s3_inspector import S3Inspector
from aspare.providers.aws.s3_remediator import S3Remediator
from aspare.providers.registry import UnsupportedProviderError


class AwsS3Provider:
    provider = Provider.AWS

    def __init__(self, inspector: S3Inspector, remediator: S3Remediator) -> None:
        self._inspector = inspector
        self._remediator = remediator

    def inspector(self, resource_type: ResourceType) -> StorageInspector:
        if resource_type is not ResourceType.S3_BUCKET:
            raise UnsupportedProviderError(
                f"AWS resource type {resource_type.value} is outside the S3 storage milestone"
            )
        return self._inspector

    def remediator(self, resource_type: ResourceType) -> StorageRemediator:
        if resource_type is not ResourceType.S3_BUCKET:
            raise UnsupportedProviderError(
                f"AWS resource type {resource_type.value} is outside the S3 storage milestone"
            )
        return self._remediator
