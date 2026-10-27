from datetime import UTC, datetime, timedelta

import pytest

from aspare.core.enums import EventType, Provider, ResourceType, RiskDecision, Severity
from aspare.core.models import (
    AclState,
    BucketPolicyState,
    EncryptionState,
    Finding,
    OwnershipState,
    PublicAccessBlockState,
    StorageEvent,
    StorageResource,
    VersioningState,
)
from aspare.intelligence import AnomalyDetector, FusionEngine


def _event(i: int, actor="arn:aws:iam::1:root", name="PutBucketPublicAccessBlock", minutes=0, hour=13, bucket="b"):
    ts = datetime(2026, 4, 5, hour, 0, tzinfo=UTC) + timedelta(minutes=minutes)
    return StorageEvent(
        event_id=f"e{i}",
        provider=Provider.AWS,
        event_type=EventType.CLOUDTRAIL_API_CALL,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=bucket,
        actor=actor,
        timestamp=ts,
        region="us-east-1",
        correlation_id=f"c{i}",
        metadata={
            "event_name": name,
            "request_parameters": {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": False,
                    "IgnorePublicAcls": False,
                    "BlockPublicPolicy": False,
                    "RestrictPublicBuckets": False,
                }
            },
        },
    )


def _resource(tags, bucket="b"):
    return StorageResource(
        provider=Provider.AWS,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=bucket,
        region="us-east-1",
        tags=tags,
        public_access_block=PublicAccessBlockState(),
        encryption=EncryptionState(),
        versioning=VersioningState(),
        policy=BucketPolicyState(),
        acl=AclState(),
        ownership=OwnershipState(),
        inspected_at=datetime.now(UTC),
    )


def _finding(rule="S3_PUBLIC_ACCESS", severity=Severity.CRITICAL, decision=RiskDecision.AUTO_REMEDIATE, bucket="b"):
    from aspare.core.enums import FindingStatus

    return Finding(
        finding_id=f"f-{rule}-{bucket}",
        resource_id=bucket,
        resource_type=ResourceType.S3_BUCKET,
        provider=Provider.AWS,
        rule_id=rule,
        policy_id="p",
        title="t",
        description="d",
        severity=severity,
        detected_at=datetime.now(UTC),
        auto_remediable=True,
        remediation_action="x",
        status=FindingStatus.CLASSIFIED,
        correlation_id="c",
        decision=decision,
    )


def test_no_event_means_no_behavioural_evidence():
    assert AnomalyDetector().assess(None).score is None


def test_root_full_disable_scores_high_and_explains_itself():
    a = AnomalyDetector().assess(_event(1))
    names = {s.name for s in a.signals}
    assert {"privileged_actor", "risky_action"} <= names
    assert a.score and a.score > 0.7


def test_burst_detected_from_history():
    d = AnomalyDetector()
    for i in range(3):
        d.observe(_event(i, minutes=i, bucket=f"b{i}"))
    a = d.assess(_event(9, minutes=4, bucket="b9"))
    assert any(s.name == "burst" for s in a.signals)


def test_novel_actor_needs_history():
    d = AnomalyDetector()
    assert not any(s.name == "novel_actor" for s in d.assess(_event(1, actor="new")).signals)
    for i in range(6):
        d.observe(_event(i, actor="alice"))
    assert any(s.name == "novel_actor" for s in d.assess(_event(7, actor="mallory")).signals)


def test_intended_public_bucket_is_not_auto_blocked():
    engine = FusionEngine()
    res = engine.evaluate(_finding(), _resource({"DataClass": "PUBLIC", "Purpose": "marketing"}))
    assert res.original_decision is RiskDecision.AUTO_REMEDIATE
    assert res.adjusted_decision is RiskDecision.ALERT_AND_LOG
    assert "intended-public-content" in res.rules_applied


def test_sensitive_bucket_keeps_auto_remediation_and_gets_priority():
    engine = FusionEngine()
    plain = engine.evaluate(_finding(), _resource({"DataClass": "INTERNAL"}))
    ferpa = engine.evaluate(_finding(), _resource({"DataClass": "FERPA"}))
    assert ferpa.adjusted_decision is RiskDecision.AUTO_REMEDIATE
    assert ferpa.priority > plain.priority


def test_scratch_versioning_is_log_only():
    engine = FusionEngine()
    res = engine.evaluate(
        _finding("S3_VERSIONING_DISABLED", Severity.MEDIUM, RiskDecision.ALERT_AND_LOG),
        _resource({"Purpose": "ds-scratch"}),
    )
    assert res.adjusted_decision is RiskDecision.LOG_ONLY


def test_anomaly_raises_confidence_and_can_escalate_without_auto_remediating():
    engine = FusionEngine()
    assessment = engine.observe(_event(1))
    quiet = engine.evaluate(
        _finding("S3_VERSIONING_DISABLED", Severity.MEDIUM, RiskDecision.ALERT_AND_LOG), _resource({})
    )
    loud = engine.evaluate(
        _finding("S3_VERSIONING_DISABLED", Severity.MEDIUM, RiskDecision.ALERT_AND_LOG),
        _resource({}),
        assessment,
        _event(1),
    )
    assert loud.confidence > quiet.confidence and loud.priority > quiet.priority
    assert loud.adjusted_decision is RiskDecision.ALERT_AND_LOG
    assert loud.escalate


def test_fusion_never_raises_to_auto_remediate():
    engine = FusionEngine()
    res = engine.evaluate(
        _finding(decision=RiskDecision.ALERT_AND_LOG), _resource({"DataClass": "FERPA"}), engine.observe(_event(1))
    )
    assert res.adjusted_decision is RiskDecision.ALERT_AND_LOG


def test_low_confidence_blocks_auto_remediation():
    engine = FusionEngine(policy={**FusionEngine().__dict__["_policy"], "min_confidence_for_auto_remediation": 0.99})
    res = engine.evaluate(_finding(), _resource({}))
    assert res.adjusted_decision is RiskDecision.ALERT_AND_LOG


def test_correlation_builds_incidents():
    engine = FusionEngine()
    results = [
        engine.evaluate(_finding("S3_PUBLIC_ACCESS"), _resource({})),
        engine.evaluate(_finding("S3_PUBLIC_ACL_EXPOSURE", Severity.CRITICAL), _resource({})),
    ]
    kinds = {i.kind for i in engine.correlate(results)}
    assert "public-exposure-chain" in kinds


@pytest.mark.parametrize("n", [3, 4])
def test_actor_campaign_needs_three_buckets(n):
    engine = FusionEngine()
    results = []
    for i in range(n):
        ev = _event(i, minutes=i, bucket=f"b{i}")
        results.append(engine.evaluate(_finding(bucket=f"b{i}"), _resource({}, f"b{i}"), engine.observe(ev), ev))
    assert any(i.kind == "actor-campaign" for i in engine.correlate(results))


def test_benchmark_fused_beats_rule_only_on_safety_and_noise():
    from aspare.intelligence.benchmark import run

    result = run()
    ro, fu = result["rule_only"], result["fused"]
    assert fu["unsafe_auto_remediations"] < ro["unsafe_auto_remediations"]
    assert fu["needless_alerts"] <= ro["needless_alerts"]
    assert fu["missed_auto_remediations"] == 0
    assert fu["decision_accuracy"] > ro["decision_accuracy"]
    assert fu["precision_at_k_urgent"] >= ro["precision_at_k_urgent"]


def test_config_resolves_from_aspare_root_like_the_lambda_package(tmp_path, monkeypatch, repo_root):
    import shutil

    shutil.copytree(repo_root / "config", tmp_path / "config")
    monkeypatch.setenv("ASPARE_ROOT", str(tmp_path))
    engine = FusionEngine()  # would raise FileNotFoundError if it still looked next to the source tree
    assert engine.evaluate(_finding(), _resource({})).confidence > 0


def test_fusion_result_round_trips():
    from aspare.intelligence.fusion import FusionResult

    res = FusionEngine().evaluate(_finding(), _resource({"DataClass": "PUBLIC", "Purpose": "marketing"}))
    again = FusionResult.from_dict(res.to_dict())
    assert again.adjusted_decision is res.adjusted_decision and again.rules_applied == res.rules_applied
