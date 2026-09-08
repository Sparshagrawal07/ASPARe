"""Serializable domain models for ASPARe's deterministic pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from aspare.core.enums import (
    ActionResultStatus,
    EventType,
    FindingStatus,
    Provider,
    ResourceType,
    RiskDecision,
    Severity,
    VerificationOutcome,
)
from aspare.core.timeutil import utcnow


def to_jsonable(obj: Any) -> Any:
    """Convert dataclasses/enums/datetimes into JSON-serializable structures."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value") and not isinstance(obj, str):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    return obj


@dataclass(frozen=True)
class PublicAccessBlockState:
    block_public_acls: bool | None = None
    ignore_public_acls: bool | None = None
    block_public_policy: bool | None = None
    restrict_public_buckets: bool | None = None
    present: bool = False
    error: str | None = None

    def all_blocked(self) -> bool:
        return bool(
            self.present
            and self.block_public_acls
            and self.ignore_public_acls
            and self.block_public_policy
            and self.restrict_public_buckets
        )


@dataclass(frozen=True)
class EncryptionState:
    enabled: bool = False
    algorithm: str | None = None
    kms_key_id: str | None = None
    bucket_key_enabled: bool | None = None
    present: bool = False
    error: str | None = None


@dataclass(frozen=True)
class VersioningState:
    status: str | None = None
    present: bool = False
    error: str | None = None

    def is_enabled(self) -> bool:
        return (self.status or "").lower() == "enabled"


@dataclass(frozen=True)
class BucketPolicyState:
    document: dict[str, Any] | None = None
    present: bool = False
    error: str | None = None


@dataclass(frozen=True)
class AclGrant:
    grantee_type: str
    grantee_uri: str | None
    grantee_id: str | None
    permission: str


@dataclass(frozen=True)
class AclState:
    owner_id: str | None = None
    grants: tuple[AclGrant, ...] = ()
    present: bool = False
    error: str | None = None


@dataclass(frozen=True)
class OwnershipState:
    object_ownership: str | None = None
    present: bool = False
    error: str | None = None

    def acls_disabled(self) -> bool:
        return (self.object_ownership or "") == "BucketOwnerEnforced"


@dataclass(frozen=True)
class StorageEvent:
    event_id: str
    provider: Provider
    event_type: EventType
    resource_type: ResourceType
    resource_id: str
    actor: str
    timestamp: datetime
    region: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class StorageResource:
    provider: Provider
    resource_type: ResourceType
    resource_id: str
    region: str
    tags: dict[str, str]
    public_access_block: PublicAccessBlockState
    encryption: EncryptionState
    versioning: VersioningState
    policy: BucketPolicyState
    acl: AclState
    ownership: OwnershipState
    inspected_at: datetime
    inspection_errors: tuple[str, ...] = ()

    def snapshot(self) -> dict[str, Any]:
        return to_jsonable(
            {
                "resource_id": self.resource_id,
                "provider": self.provider,
                "resource_type": self.resource_type,
                "region": self.region,
                "tags": self.tags,
                "public_access_block": self.public_access_block,
                "encryption": self.encryption,
                "versioning": self.versioning,
                "policy": self.policy,
                "acl": self.acl,
                "ownership": self.ownership,
                "inspection_errors": self.inspection_errors,
            }
        )


@dataclass(frozen=True)
class PolicyDefinition:
    policy_id: str
    title: str
    description: str
    control_objective: str
    resource_type: ResourceType
    rule_id: str
    expected_evidence: tuple[str, ...]
    severity: Severity
    remediation_action: str
    auto_remediable: bool
    verification_rule: str
    standards: tuple[str, ...]
    enabled: bool = True


@dataclass
class Finding:
    finding_id: str
    resource_id: str
    resource_type: ResourceType
    provider: Provider
    rule_id: str
    policy_id: str
    title: str
    description: str
    severity: Severity
    detected_at: datetime
    auto_remediable: bool
    remediation_action: str
    status: FindingStatus
    correlation_id: str
    event_id: str | None = None
    region: str = ""
    decision: RiskDecision | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    before_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        detected = data["detected_at"]
        if isinstance(detected, str):
            detected = datetime.fromisoformat(detected)
        decision = data.get("decision")
        return cls(
            finding_id=data["finding_id"],
            resource_id=data["resource_id"],
            resource_type=ResourceType(data["resource_type"]),
            provider=Provider(data["provider"]),
            rule_id=data["rule_id"],
            policy_id=data["policy_id"],
            title=data["title"],
            description=data["description"],
            severity=Severity(data["severity"]),
            detected_at=detected,
            auto_remediable=bool(data["auto_remediable"]),
            remediation_action=data["remediation_action"],
            status=FindingStatus(data["status"]),
            correlation_id=data["correlation_id"],
            event_id=data.get("event_id"),
            region=data.get("region", ""),
            decision=RiskDecision(decision) if decision else None,
            metadata=dict(data.get("metadata") or {}),
            before_state=dict(data.get("before_state") or {}),
        )


@dataclass
class ClassifiedFinding:
    finding: Finding
    decision: RiskDecision


@dataclass
class RemediationActionResult:
    action_id: str
    finding_id: str
    status: ActionResultStatus
    message: str
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False

    def succeeded(self) -> bool:
        return self.status in {ActionResultStatus.SUCCESS, ActionResultStatus.DRY_RUN}

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class VerificationResult:
    finding_id: str
    rule_id: str
    outcome: VerificationOutcome
    verified: bool
    message: str
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    remaining_finding: Finding | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass
class AuditRecord:
    record_id: str
    timestamp: datetime
    resource_id: str
    action: str
    result: str
    correlation_id: str
    finding_id: str | None = None
    rule_id: str | None = None
    policy_id: str | None = None
    severity: Severity | None = None
    verified: bool | None = None
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    actor: str | None = None
    event_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = to_jsonable(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditRecord:
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        severity = data.get("severity")
        return cls(
            record_id=data["record_id"],
            timestamp=ts,
            resource_id=data.get("resource_id", ""),
            action=data.get("action", ""),
            result=data.get("result", ""),
            correlation_id=data.get("correlation_id", ""),
            finding_id=data.get("finding_id"),
            rule_id=data.get("rule_id"),
            policy_id=data.get("policy_id"),
            severity=Severity(severity) if severity else None,
            verified=data.get("verified"),
            before_state=dict(data.get("before_state") or {}),
            after_state=dict(data.get("after_state") or {}),
            actor=data.get("actor"),
            event_id=data.get("event_id"),
            details=dict(data.get("details") or {}),
        )


@dataclass
class DetectionOutcome:
    event: StorageEvent
    resources: list[StorageResource]
    findings: list[Finding]
    classified: list[ClassifiedFinding]
    errors: list[str] = field(default_factory=list)


@dataclass
class RemediationOutcome:
    finding: Finding
    action_result: RemediationActionResult
    verification: VerificationResult
    status: FindingStatus


def empty_resource(resource_id: str, region: str = "us-east-1") -> StorageResource:
    now = utcnow()
    return StorageResource(
        provider=Provider.AWS,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=resource_id,
        region=region,
        tags={},
        public_access_block=PublicAccessBlockState(),
        encryption=EncryptionState(),
        versioning=VersioningState(),
        policy=BucketPolicyState(),
        acl=AclState(),
        ownership=OwnershipState(),
        inspected_at=now,
        inspection_errors=(),
    )
