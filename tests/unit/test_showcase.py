from dataclasses import replace

import boto3
import pytest
from moto import mock_aws

from aspare.live import LiveSession, settings_for_live
from aspare.runtime import build_runtime
from aspare.showcase import (
    SCENARIOS,
    ShowcaseEvent,
    ShowcaseState,
    approve_pending,
    cleanup_bucket,
    list_showcase_buckets,
    pending_findings,
    run_scenario,
)


@pytest.fixture
def session(tmp_path):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        settings = replace(settings_for_live("us-east-1", False, str(tmp_path / "s.jsonl")))
        yield LiveSession(
            runtime=build_runtime(settings, client=client),
            client=client,
            identity={"account": "1", "arn": "arn"},
            audit_path=str(tmp_path / "s.jsonl"),
        )


def _run(session, key, autonomous=True):
    items = list(run_scenario(session, SCENARIOS[key], autonomous))
    state = items[-1]
    assert isinstance(state, ShowcaseState)
    return [i for i in items if isinstance(i, ShowcaseEvent)], state


def test_public_policy_scenario_is_detected_fixed_and_verified(session):
    events, state = _run(session, "public-policy")
    stages = [e.stage for e in events]
    assert stages[:3] == ["provision", "provision", "misconfigure"]
    assert {"detect", "classify", "remediate", "verify", "audit"} <= set(stages)
    assert {f.rule_id for f in state.findings} >= {"S3_PUBLIC_ACCESS", "S3_HTTPS_ENFORCEMENT_MISSING"}
    verified = [e for e in events if e.stage == "verify"]
    assert verified and all(e.status == "ok" for e in verified)
    pab = session.client.get_public_access_block(Bucket=state.bucket)["PublicAccessBlockConfiguration"]
    assert all(pab.values())
    assert all(e.data["reasoning"] for e in events if e.stage == "classify")


def test_versioning_waits_for_human_approval(session):
    events, state = _run(session, "versioning")
    assert not [e for e in events if e.stage == "verify"]
    held = pending_findings(state)
    assert [f.rule_id for f in held] == ["S3_VERSIONING_DISABLED"]
    event = approve_pending(session, state, held[0], "tester")
    assert event.status == "ok"
    assert session.client.get_bucket_versioning(Bucket=state.bucket)["Status"] == "Enabled"
    assert not pending_findings(state)


def test_approval_mode_changes_nothing_until_approved(session):
    events, state = _run(session, "public", autonomous=False)
    assert not [e for e in events if e.stage == "verify"]
    pab = session.client.get_public_access_block(Bucket=state.bucket)["PublicAccessBlockConfiguration"]
    assert not any(pab.values())


def test_cleanup_only_deletes_showcase_buckets(session):
    _, state = _run(session, "transport")
    assert state.bucket in list_showcase_buckets(session)
    cleanup_bucket(session, state.bucket)
    assert state.bucket not in list_showcase_buckets(session)
    session.client.create_bucket(Bucket="precious-data")
    with pytest.raises(ValueError):
        cleanup_bucket(session, "precious-data")
