from dataclasses import replace

import boto3
import pytest
from moto import mock_aws

from aspare.config.settings import Settings
from aspare.core.enums import FindingStatus, Provider
from aspare.providers.simulated import FakeAzureApi, FakeGcsApi
from aspare.runtime import build_runtime


def _settings(tmp_path, allowed):
    return replace(
        Settings.from_env(),
        allowed_buckets=frozenset(allowed),
        require_demo_tag=True,
        audit_backend="memory",
        audit_path=tmp_path / "a.jsonl",
        event_bus_name=None,
        alert_topic_arn=None,
        fusion_enabled=False,
    )


def _scan(runtime, resource_id):
    return runtime.pipeline.run_raw({"source": "aspare.scheduler", "detail": {"buckets": [resource_id], "region": "x"}})


@mock_aws
def test_gcs_public_bucket_detected_remediated_and_verified(tmp_path):
    gcs = FakeGcsApi()
    gcs.add("open-gcs", labels={"asparedemo": "true", "dataclass": "ferpa"}, public_iam=True)
    runtime = build_runtime(
        _settings(tmp_path, {"gcs://open-gcs"}), client=boto3.client("s3", region_name="us-east-1"), gcs_api=gcs
    )
    result = _scan(runtime, "gcs://open-gcs")
    rules = {f.rule_id for f in result.detection.findings}
    assert {"S3_PUBLIC_ACCESS", "S3_PUBLIC_ACL_EXPOSURE", "S3_VERSIONING_DISABLED"} <= rules
    assert "S3_HTTPS_ENFORCEMENT_MISSING" not in rules  # not applicable to GCS
    assert "S3_ENCRYPTION_DISABLED" not in rules  # always encrypted
    assert all(f.provider is Provider.GCP for f in result.detection.findings)
    fixed = {r.finding.rule_id: r for r in result.remediations}
    assert (
        fixed["S3_PUBLIC_ACCESS"].status is FindingStatus.REMEDIATED and fixed["S3_PUBLIC_ACCESS"].verification.verified
    )
    assert fixed["S3_PUBLIC_ACL_EXPOSURE"].verification.verified
    assert gcs.buckets["open-gcs"]["public_access_prevention"] == "enforced"
    assert "allUsers" not in gcs.iam["open-gcs"][0]["members"]
    assert "user:admin@example.com" in gcs.iam["open-gcs"][0]["members"]  # private grant preserved


@mock_aws
def test_azure_account_findings_fixed_and_verified(tmp_path):
    az = FakeAzureApi()
    az.add(
        "openacct",
        tags={"ASPAReDemo": "true", "DataClass": "PII"},
        public=True,
        https_only=False,
        containers=[{"name": "photos", "public_access": "blob"}, {"name": "private", "public_access": "none"}],
    )
    runtime = build_runtime(
        _settings(tmp_path, {"azure://openacct"}), client=boto3.client("s3", region_name="us-east-1"), azure_api=az
    )
    result = _scan(runtime, "azure://openacct")
    rules = {f.rule_id for f in result.detection.findings}
    assert {
        "S3_PUBLIC_ACCESS",
        "S3_HTTPS_ENFORCEMENT_MISSING",
        "S3_PUBLIC_ACL_EXPOSURE",
        "S3_VERSIONING_DISABLED",
    } <= rules
    verified = {r.finding.rule_id for r in result.remediations if r.verification.verified}
    assert {"S3_PUBLIC_ACCESS", "S3_HTTPS_ENFORCEMENT_MISSING", "S3_PUBLIC_ACL_EXPOSURE"} <= verified
    assert az.accounts["openacct"]["allow_blob_public_access"] is False
    assert az.accounts["openacct"]["https_only"] is True
    assert [c["public_access"] for c in az.containers["openacct"]] == ["none", "none"]


@mock_aws
def test_safety_gate_blocks_untagged_cloud_resources(tmp_path):
    gcs = FakeGcsApi()
    gcs.add("not-ours", labels={"dataclass": "ferpa"}, public_iam=True)  # missing asparedemo label
    runtime = build_runtime(
        _settings(tmp_path, {"gcs://not-ours"}), client=boto3.client("s3", region_name="us-east-1"), gcs_api=gcs
    )
    result = _scan(runtime, "gcs://not-ours")
    assert result.remediations and not any(r.verification.verified for r in result.remediations)
    assert gcs.buckets["not-ours"]["public_access_prevention"] == "inherited"
    assert gcs.iam["not-ours"][0]["members"].count("allUsers") == 1


@mock_aws
def test_one_runtime_serves_aws_azure_and_gcs_together(tmp_path):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="aws-b")
    s3.put_bucket_tagging(Bucket="aws-b", Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}]})
    gcs, az = FakeGcsApi(), FakeAzureApi()
    gcs.add("g", labels={"asparedemo": "true"}, public_iam=False)
    az.add("a", tags={"ASPAReDemo": "true"}, public=False, https_only=True)
    allowed = {"aws-b", "gcs://g", "azure://a"}
    runtime = build_runtime(_settings(tmp_path, allowed), client=s3, gcs_api=gcs, azure_api=az)
    seen = set()
    for rid in allowed:
        seen |= {f.provider for f in _scan(runtime, rid).detection.findings}
    assert seen == {Provider.AWS, Provider.AZURE, Provider.GCP}
    assert set(runtime.inspector.list_resource_ids()) >= {"aws-b"}


@pytest.mark.parametrize("rid", ["gcs://x", "azure://y"])
def test_unconfigured_cloud_raises_clear_error(tmp_path, rid):
    with mock_aws():
        runtime = build_runtime(_settings(tmp_path, {rid}), client=boto3.client("s3", region_name="us-east-1"))
        result = runtime.detection_workflow.run_raw({"source": "aspare.scheduler", "detail": {"buckets": [rid]}})
        assert result.errors and "not configured" in result.errors[0]
