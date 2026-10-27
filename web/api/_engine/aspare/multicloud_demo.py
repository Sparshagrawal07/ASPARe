"""No-account multi-cloud demonstration: a simulated Azure + GCS estate run through the real pipeline."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import boto3
from moto import mock_aws

from aspare.config.settings import Settings
from aspare.core.models import RemediationOutcome
from aspare.providers.simulated import FakeAzureApi, FakeGcsApi
from aspare.runtime import build_runtime


@dataclass
class MultiCloudRun:
    rows: list[dict[str, Any]]
    before: dict[str, Any]
    after: dict[str, Any]


def _estate() -> tuple[FakeAzureApi, FakeGcsApi]:
    az, gcs = FakeAzureApi(), FakeGcsApi()
    az.add(
        "studentportalprod",
        tags={"ASPAReDemo": "true", "DataClass": "FERPA", "Environment": "prod"},
        public=True,
        https_only=False,
        containers=[{"name": "transcripts", "public_access": "blob"}, {"name": "logs", "public_access": "none"}],
    )
    az.add(
        "campusmediaweb",
        tags={"ASPAReDemo": "true", "DataClass": "PUBLIC", "Purpose": "marketing"},
        public=True,
        https_only=True,
    )
    gcs.add(
        "research-irb-consents",
        labels={"asparedemo": "true", "dataclass": "phi", "environment": "prod"},
        public_iam=True,
    )
    gcs.add(
        "ml-scratch-bucket", labels={"asparedemo": "true", "purpose": "scratch", "environment": "dev"}, public_iam=False
    )
    return az, gcs


def run_demo(tmp_audit: str = "var/audit/multicloud.jsonl") -> MultiCloudRun:
    az, gcs = _estate()
    ids = [f"azure://{n}" for n in az.accounts] + [f"gcs://{n}" for n in gcs.buckets]
    before = {
        "azure": {k: dict(v) for k, v in az.accounts.items()},
        "gcs": {k: dict(v) for k, v in gcs.buckets.items()},
    }
    with mock_aws():
        settings = replace(
            Settings.from_env(),
            allowed_buckets=frozenset(ids),
            audit_backend="memory",
            event_bus_name=None,
            alert_topic_arn=None,
        )
        runtime = build_runtime(settings, client=boto3.client("s3", region_name="us-east-1"), azure_api=az, gcs_api=gcs)
        rows: list[dict[str, Any]] = []
        for rid in ids:
            result = runtime.pipeline.run_raw({"source": "aspare.scheduler", "detail": {"buckets": [rid]}})
            fixed: dict[str, RemediationOutcome] = {r.finding.finding_id: r for r in result.remediations}
            for f in result.detection.findings:
                fusion = f.metadata.get("fusion") or {}
                outcome = fixed.get(f.finding_id)
                rows.append(
                    {
                        "cloud": f.provider.value,
                        "resource": rid,
                        "rule": f.rule_id,
                        "severity": f.severity.value,
                        "rule_only": fusion.get("original_decision"),
                        "fused": fusion.get("adjusted_decision"),
                        "confidence": fusion.get("confidence"),
                        "result": ("VERIFIED" if outcome and outcome.verification.verified else "FAILED")
                        if outcome
                        else "held for human",
                    }
                )
    after = {"azure": {k: dict(v) for k, v in az.accounts.items()}, "gcs": {k: dict(v) for k, v in gcs.buckets.items()}}
    return MultiCloudRun(rows=rows, before=before, after=after)
