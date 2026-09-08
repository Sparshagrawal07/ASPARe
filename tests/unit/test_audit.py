from aspare.audit.repository import MemoryAuditRepository, build_record
from aspare.core.enums import AuditAction, Severity
from aspare.core.models import Finding, FindingStatus, Provider, ResourceType
from aspare.core.timeutil import utcnow


def test_audit_record_creation_and_round_trip():
    finding = Finding(
        finding_id="fnd-abc",
        resource_id="demo-bucket",
        resource_type=ResourceType.S3_BUCKET,
        provider=Provider.AWS,
        rule_id="S3_PUBLIC_ACCESS",
        policy_id="POL-S3-PUBLIC-ACCESS",
        title="t",
        description="d",
        severity=Severity.CRITICAL,
        detected_at=utcnow(),
        auto_remediable=True,
        remediation_action="S3_BLOCK_PUBLIC_ACCESS",
        status=FindingStatus.DETECTED,
        correlation_id="cor-1",
        before_state={"public": True},
    )
    record = build_record(
        action=AuditAction.REMEDIATION_EXECUTED.value,
        result="SUCCESS",
        resource_id="demo-bucket",
        correlation_id="cor-1",
        finding=finding,
        verified=True,
        after_state={"public": False},
        details={"action_id": "S3_BLOCK_PUBLIC_ACCESS"},
    )
    repo = MemoryAuditRepository()
    repo.append(record)
    stored = repo.list_records()[0]
    payload = stored.to_dict()
    assert payload["finding_id"] == "fnd-abc"
    assert payload["rule"] if False else payload["rule_id"] == "S3_PUBLIC_ACCESS"
    assert payload["severity"] == "CRITICAL"
    assert payload["action"] == "REMEDIATION_EXECUTED"
    assert payload["result"] == "SUCCESS"
    assert payload["verified"] is True
    assert payload["before_state"]["public"] is True
    assert payload["after_state"]["public"] is False
    restored = type(stored).from_dict(payload)
    assert restored.finding_id == stored.finding_id
