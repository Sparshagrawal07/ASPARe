from aspare.config.settings import Settings
from aspare.core.enums import ActionResultStatus
from aspare.core.models import Finding, FindingStatus, Provider, ResourceType, Severity
from aspare.core.timeutil import utcnow
from aspare.remediation.actions.s3.public_access import BlockPublicAccessAction
from aspare.remediation.engine import RemediationEngine
from aspare.remediation.safety import SafetyGate


class RecordingRemediator:
    def __init__(self):
        self.calls = []
        self.tags = {"ASPAReDemo": "true"}

    def enable_public_access_block(self, resource_id):
        self.calls.append(resource_id)
        return {"BlockPublicAcls": True}

    def get_tags(self, resource_id):
        return self.tags


def _finding(resource="demo-bucket") -> Finding:
    return Finding(
        finding_id="fnd-1",
        resource_id=resource,
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
        status=FindingStatus.PENDING_REMEDIATION,
        correlation_id="cor-1",
    )


def test_action_selection_and_execution(settings: Settings):
    remediator = RecordingRemediator()
    engine = RemediationEngine(
        [BlockPublicAccessAction(remediator, settings, SafetyGate(settings))]
    )
    finding = _finding()
    selected = engine.select(finding)
    assert selected is not None
    assert selected.action_id == "S3_BLOCK_PUBLIC_ACCESS"
    result = engine.execute(finding)
    assert result.status is ActionResultStatus.SUCCESS
    assert remediator.calls == ["demo-bucket"]


def test_safety_gate_denies_unlisted_bucket(settings: Settings):
    remediator = RecordingRemediator()
    engine = RemediationEngine(
        [BlockPublicAccessAction(remediator, settings, SafetyGate(settings))]
    )
    result = engine.execute(_finding("other-bucket"))
    assert result.status is ActionResultStatus.DENIED
    assert remediator.calls == []


def test_unsupported_action_status(settings: Settings):
    engine = RemediationEngine([])
    result = engine.execute(_finding())
    assert result.status is ActionResultStatus.UNSUPPORTED
