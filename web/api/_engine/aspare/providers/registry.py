"""Provider registry: AWS S3 always; Azure Blob Storage and Google Cloud Storage when configured."""

from aspare.core.enums import Provider, ResourceType
from aspare.core.interfaces import StorageInspector, StorageProvider, StorageRemediator


class UnsupportedProviderError(NotImplementedError):
    pass


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[Provider, StorageProvider] = {}

    def register(self, provider: StorageProvider) -> None:
        self._providers[provider.provider] = provider

    def get(self, provider: Provider) -> StorageProvider:
        if provider not in self._providers:
            raise UnsupportedProviderError(
                f"{provider.value} storage adapter is not configured. Set ASPARE_AZURE_SUBSCRIPTION_ID + "
                "ASPARE_AZURE_RESOURCE_GROUP for Azure Blob Storage, or ASPARE_GCP_ENABLED=true for Google "
                "Cloud Storage (install aspare[azure] / aspare[gcp])."
            )
        return self._providers[provider]

    def inspector(self, provider: Provider, resource_type: ResourceType) -> StorageInspector:
        return self.get(provider).inspector(resource_type)

    def remediator(self, provider: Provider, resource_type: ResourceType) -> StorageRemediator:
        return self.get(provider).remediator(resource_type)
