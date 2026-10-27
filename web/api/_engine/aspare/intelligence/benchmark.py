"""Rule-only vs fused triage benchmark on a synthetic, hand-labelled case set (see data/benchmark/cases.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aspare.core.enums import EventType, FindingStatus, Provider, ResourceType, RiskDecision
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
from aspare.intelligence.fusion import FusionEngine
from aspare.policy.registry import PolicyRegistry
from aspare.risk.evaluator import RiskEvaluator, RiskPolicy

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES = ROOT / "data" / "benchmark" / "cases.json"
_EXPECTED_RANK = {"ignore": 0, "alert": 1, "auto_fix": 2}


def _label(decision: RiskDecision) -> str:
    return {
        RiskDecision.AUTO_REMEDIATE: "auto_fix",
        RiskDecision.ALERT_AND_LOG: "alert",
        RiskDecision.MANUAL_REVIEW: "alert",
        RiskDecision.LOG_ONLY: "ignore",
    }[decision]


@dataclass
class Row:
    case_id: str
    expected: str
    urgent: bool
    rule_only: str
    fused: str
    rule_priority: float
    fused_priority: float


def _build(
    case: dict[str, Any], registry: PolicyRegistry, index: int
) -> tuple[Finding, StorageResource, StorageEvent | None]:
    policy = registry.by_rule(case["rule"])
    bucket = f"bench-{case['id']}"
    resource = StorageResource(
        provider=Provider.AWS,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=bucket,
        region="us-east-1",
        tags=case["tags"],
        public_access_block=PublicAccessBlockState(),
        encryption=EncryptionState(),
        versioning=VersioningState(),
        policy=BucketPolicyState(),
        acl=AclState(),
        ownership=OwnershipState(),
        inspected_at=datetime.now(UTC),
        inspection_errors=tuple(case.get("inspection_errors") or ()),
    )
    finding = Finding(
        finding_id=f"bf-{case['id']}",
        resource_id=bucket,
        resource_type=ResourceType.S3_BUCKET,
        provider=Provider.AWS,
        rule_id=policy.rule_id,
        policy_id=policy.policy_id,
        title=policy.title,
        description=policy.description,
        severity=policy.severity,
        detected_at=datetime.now(UTC),
        auto_remediable=policy.auto_remediable,
        remediation_action=policy.remediation_action,
        status=FindingStatus.CLASSIFIED,
        correlation_id=f"bc-{case['id']}",
        before_state={"inspection_errors": list(case.get("inspection_errors") or ())},
    )
    event = None
    if case.get("event"):
        ev = case["event"]
        event = StorageEvent(
            event_id=f"be-{case['id']}",
            provider=Provider.AWS,
            event_type=EventType.CLOUDTRAIL_API_CALL,
            resource_type=ResourceType.S3_BUCKET,
            resource_id=bucket,
            actor=ev["actor"],
            timestamp=datetime(2026, 4, 5, ev.get("hour", 12), 0, tzinfo=UTC) + timedelta(minutes=ev.get("minute", 0)),
            region="us-east-1",
            correlation_id=f"bc-{case['id']}",
            metadata={
                "event_name": ev["name"],
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
    return finding, resource, event


def run(cases_path: Path | None = None) -> dict[str, Any]:
    payload = json.loads((cases_path or DEFAULT_CASES).read_text())
    registry = PolicyRegistry.from_path(ROOT / "config" / "policies" / "s3.json")
    risk = RiskEvaluator(RiskPolicy.from_path(ROOT / "config" / "risk-policy.json"))
    fusion = FusionEngine()
    rows: list[Row] = []
    severity_weights = fusion._policy["severity_weights"]  # noqa: SLF001 - same weights the rule-only baseline ranks by
    for index, case in enumerate(payload["cases"]):
        finding, resource, event = _build(case, registry, index)
        finding.decision = risk.evaluate(finding)
        base = finding.decision
        assessment = fusion.observe(event) if event else None
        result = fusion.evaluate(finding, resource, assessment, event)
        rows.append(
            Row(
                case["id"],
                case["expected"],
                bool(case["urgent"]),
                _label(base),
                _label(result.adjusted_decision),
                float(severity_weights[finding.severity.value]),
                result.priority,
            )
        )

    def metrics(key: str, ranker: str) -> dict[str, Any]:
        unsafe = sum(1 for r in rows if getattr(r, key) == "auto_fix" and r.expected != "auto_fix")
        missed = sum(1 for r in rows if r.expected == "auto_fix" and getattr(r, key) != "auto_fix")
        noise = sum(1 for r in rows if getattr(r, key) == "alert" and r.expected == "ignore")
        correct = sum(1 for r in rows if getattr(r, key) == r.expected)
        urgent_total = sum(1 for r in rows if r.urgent)
        ranked = sorted(rows, key=lambda r: -getattr(r, ranker))  # stable: ties keep input order
        k = urgent_total
        hits = sum(1 for r in ranked[:k] if r.urgent)
        return {
            "decision_accuracy": round(correct / len(rows), 3),
            "unsafe_auto_remediations": unsafe,
            "missed_auto_remediations": missed,
            "needless_alerts": noise,
            "precision_at_k_urgent": round(hits / k, 3) if k else None,
            "k": k,
        }

    return {
        "cases": len(rows),
        "rule_only": metrics("rule_only", "rule_priority"),
        "fused": metrics("fused", "fused_priority"),
        "rows": [r.__dict__ for r in rows],
    }
