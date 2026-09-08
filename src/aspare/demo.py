"""Safe demonstration of the deterministic ASPARe pipeline."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import replace
from typing import Any

import boto3

from aspare.config.settings import Settings
from aspare.core.enums import FindingStatus, RiskDecision
from aspare.runtime import build_runtime
from aspare.s3.https_policy import PUBLIC_ACL_URIS


def _print(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2, default=str, sort_keys=True))


def _configure_insecure_bucket(client: Any, bucket: str) -> None:
    client.create_bucket(Bucket=bucket)
    client.put_bucket_tagging(
        Bucket=bucket,
        Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}]},
    )
    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    try:
        client.put_bucket_acl(Bucket=bucket, ACL="public-read")
    except Exception:
        # Some environments refuse public ACLs; the remaining controls still demonstrate the pipeline.
        pass


def _settings_for(bucket: str, audit_path: str) -> Settings:
    base = Settings.from_env()
    return replace(
        base,
        allowed_buckets=frozenset({bucket}),
        require_demo_tag=True,
        dry_run=False,
        audit_backend="jsonl",
        audit_path=type(base.audit_path)(audit_path),
        event_bus_name=None,
    )


def _run_against_client(client: Any, bucket: str, audit_path: str) -> dict[str, Any]:
    runtime = build_runtime(_settings_for(bucket, audit_path), client=client)
    event = {
        "id": f"demo-{bucket}",
        "source": "aspare.demo",
        "detail-type": "ASPARe Direct Scan",
        "detail": {"bucket": bucket, "actor": "aspare.demo", "region": "us-east-1"},
    }
    result = runtime.pipeline.run_raw(event)
    summary = {
        "bucket": bucket,
        "resources": [item.resource_id for item in result.detection.resources],
        "findings": [
            {
                "rule": item.rule_id,
                "severity": item.severity.value,
                "decision": (item.decision.value if item.decision else None),
                "status": item.status.value,
                "action": item.remediation_action,
            }
            for item in result.detection.findings
        ],
        "remediations": [
            {
                "rule": item.finding.rule_id,
                "action": item.action_result.action_id,
                "action_status": item.action_result.status.value,
                "verified": item.verification.verified,
                "verification": item.verification.outcome.value,
                "final_status": item.status.value,
            }
            for item in result.remediations
        ],
        "audit_path": audit_path,
        "public_acl_uris": sorted(PUBLIC_ACL_URIS),
    }
    public = result.finding_by_rule("S3_PUBLIC_ACCESS")
    https = result.finding_by_rule("S3_HTTPS_ENFORCEMENT_MISSING")
    summary["acceptance"] = {
        "public_access_detected": public is not None and public.severity.value == "CRITICAL",
        "public_access_auto_remediated": any(
            item.finding.rule_id == "S3_PUBLIC_ACCESS"
            and item.status is FindingStatus.REMEDIATED
            and item.verification.verified
            for item in result.remediations
        ),
        "https_detected": https is not None,
        "https_auto_remediated": any(
            item.finding.rule_id == "S3_HTTPS_ENFORCEMENT_MISSING"
            and item.status is FindingStatus.REMEDIATED
            and item.verification.verified
            for item in result.remediations
        ),
        "versioning_not_auto_remediated": all(
            classified.decision is not RiskDecision.AUTO_REMEDIATE
            for classified in result.detection.classified
            if classified.finding.rule_id == "S3_VERSIONING_DISABLED"
        ),
    }
    return summary


def run_mocked_demo() -> dict[str, Any]:
    from moto import mock_aws

    bucket = f"aspare-demo-{uuid.uuid4().hex[:10]}"
    audit_path = os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        _configure_insecure_bucket(client, bucket)
        summary = _run_against_client(client, bucket, audit_path)
    _print("ASPARe mocked demonstration", summary)
    _print(
        "Pipeline",
        "INSECURE CONFIGURATION → DETECTION → FINDING → RISK EVALUATION → "
        "AUTOMATIC REMEDIATION → VERIFICATION → AUDIT RECORD → DASHBOARD",
    )
    return summary


def run_live_demo(confirm: str, cleanup: bool = False) -> dict[str, Any]:
    if confirm != "ASPARE-LIVE-DEMO":
        raise SystemExit(
            "Refusing live AWS demo. Re-run with --mode live --confirm ASPARE-LIVE-DEMO. "
            "This creates one uniquely named bucket tagged ASPAReDemo=true and does not "
            "target unrelated buckets."
        )
    suffix = uuid.uuid4().hex[:10]
    bucket = f"aspare-demo-{suffix}"
    region = os.environ.get("AWS_REGION") or os.environ.get("ASPARE_REGION") or "us-east-1"
    client = boto3.client("s3", region_name=region)
    _configure_insecure_bucket(client, bucket)
    audit_path = os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl")
    try:
        summary = _run_against_client(client, bucket, audit_path)
        summary["live_bucket"] = bucket
        _print("ASPARe live demonstration", summary)
        return summary
    finally:
        if cleanup:
            try:
                client.delete_bucket(Bucket=bucket)
                _print("Cleanup", f"Deleted {bucket}")
            except Exception as exc:  # noqa: BLE001
                _print("Cleanup failed", str(exc))
