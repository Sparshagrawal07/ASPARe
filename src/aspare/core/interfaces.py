"""Injectable protocols for ASPARe's layered architecture."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from aspare.core.enums import Provider, ResourceType
from aspare.core.models import (
    AuditRecord,
    Finding,
    PolicyDefinition,
    RemediationActionResult,
    StorageResource,
)


@runtime_checkable
class DetectionRule(Protocol):
    rule_id: str
    name: str
    description: str

    def supports(self, resource: StorageResource) -> bool: ...

    def detect(self, resource: StorageResource) -> Finding | None: ...


@runtime_checkable
class StorageInspector(Protocol):
    provider: Provider
    resource_type: ResourceType

    def inspect(self, resource_id: str, region: str | None = None) -> StorageResource: ...

    def list_resource_ids(self) -> list[str]: ...


@runtime_checkable
class StorageRemediator(Protocol):
    provider: Provider
    resource_type: ResourceType

    def enable_public_access_block(self, resource_id: str) -> dict[str, Any]: ...

    def enable_default_encryption(
        self, resource_id: str, algorithm: str, kms_key_id: str | None
    ) -> dict[str, Any]: ...

    def enable_versioning(self, resource_id: str) -> dict[str, Any]: ...

    def merge_secure_transport_policy(
        self, resource_id: str, statement: dict[str, Any]
    ) -> dict[str, Any]: ...

    def remove_public_acl_grants(self, resource_id: str) -> dict[str, Any]: ...

    def get_tags(self, resource_id: str) -> dict[str, str]: ...


@runtime_checkable
class StorageProvider(Protocol):
    """Provider adapter contract. Azure/GCP remain unimplemented extension points."""

    provider: Provider

    def inspector(self, resource_type: ResourceType) -> StorageInspector: ...

    def remediator(self, resource_type: ResourceType) -> StorageRemediator: ...


@runtime_checkable
class RemediationAction(Protocol):
    action_id: str

    def supports(self, finding: Finding) -> bool: ...

    def execute(self, finding: Finding) -> RemediationActionResult: ...


@runtime_checkable
class AuditRepository(Protocol):
    def append(self, record: AuditRecord) -> None: ...

    def list_records(self) -> list[AuditRecord]: ...


@runtime_checkable
class FindingPublisher(Protocol):
    def publish(self, finding: Finding) -> None: ...


@runtime_checkable
class PolicySource(Protocol):
    def get(self, policy_id: str) -> PolicyDefinition: ...

    def by_rule(self, rule_id: str) -> PolicyDefinition: ...

    def all_enabled(self) -> list[PolicyDefinition]: ...
