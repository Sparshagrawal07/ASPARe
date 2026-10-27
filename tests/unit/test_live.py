import json
from dataclasses import replace

import boto3
import pytest
from moto import mock_aws

from aspare.live import LiveSession, approval_gate, approve, scan, settings_for_live
from aspare.runtime import build_runtime


@pytest.fixture
def session(tmp_path):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        for name, tag in (("open-tagged", "true"), ("open-untagged", "false")):
            client.create_bucket(Bucket=name)
            client.put_bucket_tagging(Bucket=name, Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": tag}]})
            client.put_public_access_block(
                Bucket=name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": False,
                    "IgnorePublicAcls": False,
                    "BlockPublicPolicy": False,
                    "RestrictPublicBuckets": False,
                },
            )
        settings = replace(settings_for_live("us-east-1", False, str(tmp_path / "live.jsonl")))
        yield LiveSession(
            runtime=build_runtime(settings, client=client),
            client=client,
            identity={"account": "123456789012", "arn": "arn:aws:iam::123456789012:user/test"},
            audit_path=str(tmp_path / "live.jsonl"),
        )


def test_scan_is_read_only_and_does_not_autoremediate(session):
    findings = scan(session)
    assert {f.resource_id for f in findings} == {"open-tagged", "open-untagged"}
    pab = session.client.get_public_access_block(Bucket="open-tagged")["PublicAccessBlockConfiguration"]
    assert pab["BlockPublicAcls"] is False
    assert len(session.inventory["buckets"]) == 2


def test_approval_gate_blocks_untagged_buckets(session):
    findings = scan(session)
    by_bucket = {(f.resource_id, f.rule_id): f for f in findings}
    ok, _ = approval_gate(session, by_bucket[("open-tagged", "S3_PUBLIC_ACCESS")])
    blocked, reason = approval_gate(session, by_bucket[("open-untagged", "S3_PUBLIC_ACCESS")])
    assert ok
    assert not blocked and "Safety gate" in reason


def test_approve_remediates_verifies_and_audits(session):
    findings = scan(session)
    target = next(f for f in findings if f.resource_id == "open-tagged" and f.rule_id == "S3_PUBLIC_ACCESS")
    outcome = approve(session, target)
    assert outcome is not None and outcome.verification.verified
    pab = session.client.get_public_access_block(Bucket="open-tagged")["PublicAccessBlockConfiguration"]
    assert pab["BlockPublicAcls"] is True
    actions = [json.loads(line)["action"] for line in open(session.audit_path)]
    assert "REMEDIATION_APPROVED" in actions and "VERIFICATION_COMPLETED" in actions


def test_unapproved_untagged_bucket_stays_unchanged(session):
    findings = scan(session)
    target = next(f for f in findings if f.resource_id == "open-untagged" and f.rule_id == "S3_PUBLIC_ACCESS")
    outcome = approve(session, target)  # gate inside the action still refuses
    assert outcome is not None and not outcome.verification.verified
    pab = session.client.get_public_access_block(Bucket="open-untagged")["PublicAccessBlockConfiguration"]
    assert pab["BlockPublicAcls"] is False


def test_dry_run_approval_is_audited_but_writes_nothing(session):
    session.runtime.settings = replace(session.runtime.settings, dry_run=True)
    findings = scan(session)
    target = next(f for f in findings if f.resource_id == "open-tagged" and f.rule_id == "S3_PUBLIC_ACCESS")
    assert approve(session, target) is None
    pab = session.client.get_public_access_block(Bucket="open-tagged")["PublicAccessBlockConfiguration"]
    assert pab["BlockPublicAcls"] is False
    rows = [json.loads(line) for line in open(session.audit_path)]
    assert any(r["action"] == "REMEDIATION_APPROVED" and r["result"] == "DRY_RUN" for r in rows)


def test_sns_alerter_notifies_for_alert_only_findings(tmp_path):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        sns = boto3.client("sns", region_name="us-east-1")
        sqs = boto3.client("sqs", region_name="us-east-1")
        topic = sns.create_topic(Name="aspare-alerts")["TopicArn"]
        queue = sqs.create_queue(QueueName="q")["QueueUrl"]
        qarn = sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=qarn)
        s3.create_bucket(Bucket="alert-me")
        s3.put_bucket_tagging(Bucket="alert-me", Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}]})
        settings = replace(settings_for_live("us-east-1", True, str(tmp_path / "a.jsonl")), alert_topic_arn=topic)
        runtime = build_runtime(settings, client=s3, sns_client=sns)
        runtime.detection_workflow.run_raw(
            {"source": "aspare.direct", "detail": {"bucket": "alert-me", "region": "us-east-1"}}
        )
        messages = sqs.receive_message(QueueUrl=queue, MaxNumberOfMessages=10).get("Messages", [])
        assert any("S3_VERSIONING_DISABLED" in m["Body"] for m in messages)
