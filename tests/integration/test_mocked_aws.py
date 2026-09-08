from __future__ import annotations

from dataclasses import replace

import boto3
import pytest
from moto import mock_aws

from aspare.core.enums import FindingStatus
from aspare.handlers.detection import detection_handler, remediation_handler, reset_runtime
from aspare.runtime import build_runtime
from aspare.s3.https_policy import has_secure_transport_deny


@pytest.fixture
def aws_env(settings):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        yield client


def _prepare(client, bucket: str, *, public: bool = True, policy: dict | None = None) -> None:
    client.create_bucket(Bucket=bucket)
    client.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}]})
    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": not public,
            "IgnorePublicAcls": not public,
            "BlockPublicPolicy": not public,
            "RestrictPublicBuckets": not public,
        },
    )
    if policy:
        import json

        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))


def test_mocked_public_access_and_https_pipeline(aws_env, settings, tmp_path):
    client = aws_env
    bucket = "demo-bucket"
    _prepare(client, bucket, public=True)
    runtime = build_runtime(replace(settings, allowed_buckets=frozenset({bucket})), client=client)
    result = runtime.pipeline.run_raw(
        {
            "source": "aspare.demo",
            "detail-type": "ASPARe Direct Scan",
            "detail": {"bucket": bucket, "actor": "test"},
        }
    )
    rules = {item.finding.rule_id: item for item in result.remediations}
    assert "S3_PUBLIC_ACCESS" in rules
    assert rules["S3_PUBLIC_ACCESS"].status is FindingStatus.REMEDIATED
    assert rules["S3_PUBLIC_ACCESS"].verification.verified is True
    assert "S3_HTTPS_ENFORCEMENT_MISSING" in rules
    assert rules["S3_HTTPS_ENFORCEMENT_MISSING"].verification.verified is True
    pab = client.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    assert all(pab.values())
    policy = client.get_bucket_policy(Bucket=bucket)["Policy"]
    import json

    assert has_secure_transport_deny(json.loads(policy), bucket)
    versioning = [item for item in result.detection.classified if item.finding.rule_id == "S3_VERSIONING_DISABLED"]
    assert versioning
    assert versioning[0].decision.value == "ALERT_AND_LOG"
    records = runtime.audit.list_records()
    assert any(record.action == "VERIFICATION_COMPLETED" and record.verified for record in records)


def test_duplicate_delivery_is_idempotent(aws_env, settings):
    client = aws_env
    bucket = "demo-bucket"
    _prepare(client, bucket, public=True)
    runtime = build_runtime(replace(settings, allowed_buckets=frozenset({bucket})), client=client)
    event = {"source": "aspare.demo", "detail-type": "ASPARe Direct Scan", "detail": {"bucket": bucket}}
    first = runtime.pipeline.run_raw(event)
    second = runtime.pipeline.run_raw(event)
    assert first.finding_by_rule("S3_PUBLIC_ACCESS") is not None
    assert second.finding_by_rule("S3_PUBLIC_ACCESS") is None


def test_handler_serialization(aws_env, settings, monkeypatch):
    client = aws_env
    bucket = "demo-bucket"
    _prepare(client, bucket, public=True)
    runtime = build_runtime(replace(settings, allowed_buckets=frozenset({bucket})), client=client)
    monkeypatch.setattr("aspare.handlers.detection.get_runtime", lambda: runtime)
    reset_runtime()
    response = detection_handler(
        {
            "id": "evt-1",
            "source": "aspare.demo",
            "detail-type": "ASPARe Direct Scan",
            "detail": {"bucket": bucket},
        }
    )
    assert response["statusCode"] == 200
    public = next(item for item in runtime.publisher.published if item.rule_id == "S3_PUBLIC_ACCESS")
    rem = remediation_handler({"detail": public.to_dict()})
    assert rem["statusCode"] == 200


def test_no_mutation_outside_allowlist(aws_env, settings):
    client = aws_env
    client.create_bucket(Bucket="other-bucket")
    client.create_bucket(Bucket="demo-bucket")
    client.put_public_access_block(
        Bucket="other-bucket",
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    runtime = build_runtime(replace(settings, allowed_buckets=frozenset({"demo-bucket"})), client=client)
    result = runtime.pipeline.run_raw(
        {"source": "aspare.demo", "detail-type": "ASPARe Direct Scan", "detail": {"bucket": "other-bucket"}}
    )
    assert result.detection.resources == []
    assert result.remediations == []
    pab = client.get_public_access_block(Bucket="other-bucket")["PublicAccessBlockConfiguration"]
    assert pab["BlockPublicAcls"] is False
