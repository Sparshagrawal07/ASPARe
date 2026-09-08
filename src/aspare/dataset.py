"""Replay a recorded S3 inventory and CloudTrail lookup through the existing pipeline."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import boto3

from aspare.config.settings import Settings
from aspare.core.enums import RiskDecision
from aspare.core.models import Finding, RemediationOutcome
from aspare.runtime import Runtime, build_runtime

_REPO = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = _REPO / "data" / "inventory" / "s3-buckets.json"
DEFAULT_EVENTS = _REPO / "data" / "cloudtrail" / "s3-lookup-events.json"


def load_inventory(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or DEFAULT_INVENTORY).read_text())


def load_events(path: Path | None = None) -> list[dict[str, Any]]:
    payload = json.loads((path or DEFAULT_EVENTS).read_text())
    events = payload.get("events") if isinstance(payload, dict) else payload
    if not isinstance(events, list):
        raise ValueError("CloudTrail dataset must be a list of events")
    return events


def seed_client(client: Any, inventory: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for bucket in inventory.get("buckets") or []:
        name = str(bucket["name"])
        names.append(name)
        client.create_bucket(Bucket=name)
        tags = bucket.get("tags") or {"ASPAReDemo": "true"}
        client.put_bucket_tagging(
            Bucket=name,
            Tagging={"TagSet": [{"Key": str(key), "Value": str(value)} for key, value in tags.items()]},
        )
        pab = bucket.get("public_access_block")
        if pab:
            client.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration=pab)
        encryption = bucket.get("encryption") or {}
        algorithm = encryption.get("algorithm")
        if algorithm:
            rule: dict[str, Any] = {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": algorithm}}
            if encryption.get("bucket_key_enabled") is not None:
                rule["BucketKeyEnabled"] = encryption["bucket_key_enabled"]
            client.put_bucket_encryption(
                Bucket=name,
                ServerSideEncryptionConfiguration={"Rules": [rule]},
            )
        versioning = (bucket.get("versioning") or {}).get("status")
        if versioning:
            client.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": versioning})
        policy = bucket.get("policy")
        if policy:
            client.put_bucket_policy(
                Bucket=name,
                Policy=policy if isinstance(policy, str) else json.dumps(policy),
            )
        acl = bucket.get("acl")
        if acl:
            try:
                client.put_bucket_acl(Bucket=name, ACL=acl)
            except Exception:
                pass
    return names


def settings_for_dataset(buckets: list[str], audit_path: str) -> Settings:
    base = Settings.from_env()
    return replace(
        base,
        allowed_buckets=frozenset(buckets),
        require_demo_tag=True,
        dry_run=False,
        audit_backend="jsonl",
        audit_path=Path(audit_path),
        event_bus_name=None,
    )


def start_lab(audit_path: str | None = None) -> dict[str, Any]:
    from moto import mock_aws

    path = audit_path or os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl")
    ctx = mock_aws()
    ctx.start()
    inventory = load_inventory()
    events = load_events()
    client = boto3.client("s3", region_name=str(inventory.get("region") or "us-east-1"))
    buckets = seed_client(client, inventory)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("")
    runtime: Runtime = build_runtime(settings_for_dataset(buckets, path), client=client)
    return {
        "ctx": ctx,
        "client": client,
        "runtime": runtime,
        "inventory": inventory,
        "events": events,
        "buckets": buckets,
        "audit_path": path,
    }


def stop_lab(lab: dict[str, Any] | None) -> None:
    if not lab:
        return
    ctx = lab.get("ctx")
    if ctx is not None:
        ctx.stop()


def detect(lab: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    runtime: Runtime = lab["runtime"]
    for raw in lab["events"]:
        outcome = runtime.detection_workflow.run_raw(raw)
        findings.extend(outcome.findings)
    return findings


def remediate(lab: dict[str, Any], findings: list[Finding]) -> list[RemediationOutcome]:
    runtime: Runtime = lab["runtime"]
    results: list[RemediationOutcome] = []
    for finding in findings:
        if finding.decision is RiskDecision.AUTO_REMEDIATE:
            results.append(runtime.remediation_workflow.run(finding))
    return results


def summarize(lab: dict[str, Any], findings: list[Finding], remediations: list[RemediationOutcome]) -> dict[str, Any]:
    return {
        "source": (lab.get("inventory") or {}).get("source"),
        "buckets": lab.get("buckets"),
        "events": [
            {
                "id": item.get("id"),
                "event_name": (item.get("detail") or {}).get("eventName"),
                "bucket": ((item.get("detail") or {}).get("requestParameters") or {}).get("bucketName"),
                "time": item.get("time"),
            }
            for item in lab.get("events") or []
        ],
        "findings": [
            {
                "resource": item.resource_id,
                "rule": item.rule_id,
                "severity": item.severity.value,
                "decision": item.decision.value if item.decision else None,
                "status": item.status.value,
            }
            for item in findings
        ],
        "remediations": [
            {
                "resource": item.finding.resource_id,
                "rule": item.finding.rule_id,
                "action": item.action_result.action_id,
                "verified": item.verification.verified,
                "status": item.status.value,
            }
            for item in remediations
        ],
        "audit_path": lab.get("audit_path"),
    }


def run_dataset_pipeline(audit_path: str | None = None) -> dict[str, Any]:
    lab = start_lab(audit_path)
    try:
        findings = detect(lab)
        remediations = remediate(lab, findings)
        summary = summarize(lab, findings, remediations)
        print(json.dumps(summary, indent=2, default=str))
        return summary
    finally:
        stop_lab(lab)
