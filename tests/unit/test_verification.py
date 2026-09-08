from tests.fixtures.builders import public_bucket, secure_bucket

from aspare.core.enums import ActionResultStatus, FindingStatus, VerificationOutcome
from aspare.core.lifecycle import InvalidLifecycleTransition, transition
from aspare.core.models import RemediationActionResult
from aspare.detection.engine import DetectionEngine
from aspare.detection.rules.s3 import default_s3_rules
from aspare.verification.engine import VerificationEngine


class FakeInspector:
    def __init__(self, resource):
        self.resource = resource
        self.fail = False

    def inspect(self, resource_id, region=None):
        if self.fail:
            raise RuntimeError("re-read failed")
        return self.resource


def _finding(policy_registry, resource=None):
    resource = resource or public_bucket()
    engine = DetectionEngine(default_s3_rules(policy_registry))
    finding = engine.evaluate_rule("S3_PUBLIC_ACCESS", resource)
    assert finding is not None
    return finding, engine


def test_verified_when_finding_disappears(policy_registry):
    finding, engine = _finding(policy_registry)
    inspector = FakeInspector(secure_bucket())
    result = VerificationEngine(inspector, engine).verify(
        finding,
        RemediationActionResult(
            action_id="S3_BLOCK_PUBLIC_ACCESS",
            finding_id=finding.finding_id,
            status=ActionResultStatus.SUCCESS,
            message="ok",
            before_state=finding.before_state,
        ),
    )
    assert result.verified is True
    assert result.outcome is VerificationOutcome.VERIFIED


def test_failed_action_is_not_verified(policy_registry):
    finding, engine = _finding(policy_registry)
    result = VerificationEngine(FakeInspector(secure_bucket()), engine).verify(
        finding,
        RemediationActionResult(
            action_id="S3_BLOCK_PUBLIC_ACCESS",
            finding_id=finding.finding_id,
            status=ActionResultStatus.FAILED,
            message="access denied",
        ),
    )
    assert result.verified is False
    assert result.outcome is VerificationOutcome.ACTION_FAILED


def test_reread_failure(policy_registry):
    finding, engine = _finding(policy_registry)
    inspector = FakeInspector(secure_bucket())
    inspector.fail = True
    result = VerificationEngine(inspector, engine).verify(
        finding,
        RemediationActionResult(
            action_id="S3_BLOCK_PUBLIC_ACCESS",
            finding_id=finding.finding_id,
            status=ActionResultStatus.SUCCESS,
            message="ok",
        ),
    )
    assert result.outcome is VerificationOutcome.REREAD_FAILED
    assert result.verified is False


def test_persistent_finding_after_remediation(policy_registry):
    finding, engine = _finding(policy_registry)
    result = VerificationEngine(FakeInspector(public_bucket()), engine).verify(
        finding,
        RemediationActionResult(
            action_id="S3_BLOCK_PUBLIC_ACCESS",
            finding_id=finding.finding_id,
            status=ActionResultStatus.SUCCESS,
            message="ok",
        ),
    )
    assert result.outcome is VerificationOutcome.FINDING_PERSISTED
    assert result.verified is False


def test_lifecycle_rejects_invalid_transition(policy_registry):
    finding, _ = _finding(policy_registry)
    try:
        transition(finding, FindingStatus.REMEDIATED)
        raise AssertionError("expected invalid transition")
    except InvalidLifecycleTransition:
        pass
