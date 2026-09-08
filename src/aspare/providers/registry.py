"""Provider adapters. Only AWS S3 is implemented in this milestone."""

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
                f"{provider.value} storage adapter is not implemented in the current ASPARe "
                "milestone. AWS S3 is the only active provider; Azure Blob Storage and Google "
                "Cloud Storage remain extension points for the remaining 50%."
            )
        return self._providers[provider]

    def inspector(self, provider: Provider, resource_type: ResourceType) -> StorageInspector:
        return self.get(provider).inspector(resource_type)

    def remediator(self, provider: Provider, resource_type: ResourceType) -> StorageRemediator:
        return self.get(provider).remediator(resource_type)
