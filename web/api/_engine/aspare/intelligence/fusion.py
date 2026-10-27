"""Fuse rule evidence, behavioural anomaly evidence and business context into confidence, priority and decision.

Confidence is an *evidence-weighted* score, not a calibrated probability:

    c0 = direct_read_confidence            (0.97 when the control was read directly from the cloud API,
                                            lower when the inspection reported errors)
    c1 = clamp(c0 + sum(context confidence deltas))
    c  = c1 + (1 - c1) * anomaly_corroboration_weight * anomaly_score      (only when behavioural evidence exists)

Priority = severity weight x c x product(context multipliers) + anomaly bonus x anomaly score.
Fusion may *lower* an automatic action to an alert (context says it may be intended, or confidence is low) but never
raises a decision to AUTO_REMEDIATE.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from aspare.config.paths import config_dir
from aspare.core.enums import RiskDecision
from aspare.core.models import Finding, StorageEvent, StorageResource
from aspare.intelligence.anomaly import AnomalyAssessment, AnomalyDetector, load_fusion_policy

_RANK = {
    RiskDecision.LOG_ONLY: 0,
    RiskDecision.ALERT_AND_LOG: 1,
    RiskDecision.MANUAL_REVIEW: 1,
    RiskDecision.AUTO_REMEDIATE: 2,
}


@dataclass
class FusionResult:
    finding_id: str
    resource_id: str
    rule_id: str
    actor: str | None
    confidence: float
    priority: float
    original_decision: RiskDecision
    adjusted_decision: RiskDecision
    escalate: bool
    reasons: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    anomaly: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FusionResult:
        return cls(
            finding_id=data["finding_id"],
            resource_id=data["resource_id"],
            rule_id=data["rule_id"],
            actor=data.get("actor"),
            confidence=float(data["confidence"]),
            priority=float(data["priority"]),
            original_decision=RiskDecision(data["original_decision"]),
            adjusted_decision=RiskDecision(data["adjusted_decision"]),
            escalate=bool(data.get("escalate")),
            reasons=list(data.get("reasons") or []),
            rules_applied=list(data.get("rules_applied") or []),
            anomaly=dict(data.get("anomaly") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "resource_id": self.resource_id,
            "rule_id": self.rule_id,
            "actor": self.actor,
            "confidence": round(self.confidence, 3),
            "priority": round(self.priority, 1),
            "original_decision": self.original_decision.value,
            "adjusted_decision": self.adjusted_decision.value,
            "escalate": self.escalate,
            "reasons": self.reasons,
            "rules_applied": self.rules_applied,
            "anomaly": self.anomaly,
        }


@dataclass
class Incident:
    incident_id: str
    kind: str
    resource_id: str
    severity: str
    finding_ids: list[str]
    summary: str


class FusionEngine:
    def __init__(
        self,
        policy: dict[str, Any] | None = None,
        context_policy: dict[str, Any] | None = None,
        detector: AnomalyDetector | None = None,
    ) -> None:
        self._policy = policy or load_fusion_policy()
        self._context = context_policy or json.loads((config_dir() / "context-policy.json").read_text(encoding="utf-8"))
        self.detector = detector or AnomalyDetector(self._policy)

    # --- public API --------------------------------------------------------------------------------------------
    def observe(self, event: StorageEvent) -> AnomalyAssessment:
        """Score an event against the learned baseline, then learn from it."""
        assessment = self.detector.assess(event)
        self.detector.observe(event)
        return assessment

    def evaluate(
        self,
        finding: Finding,
        resource: StorageResource | None,
        assessment: AnomalyAssessment | None = None,
        event: StorageEvent | None = None,
    ) -> FusionResult:
        original = finding.decision or RiskDecision.LOG_ONLY
        tags = dict(resource.tags) if resource else {}
        reasons: list[str] = []
        applied: list[str] = []

        errors = (finding.before_state or {}).get("inspection_errors") or ()
        confidence = float(
            self._policy["inspection_error_confidence"] if errors else self._policy["direct_read_confidence"]
        )
        reasons.append(
            "Control was read directly from the cloud API."
            if not errors
            else f"Inspection reported {len(errors)} error(s); evidence is less certain."
        )

        multiplier = 1.0
        decision = original
        for rule in self._context["rules"]:
            if not self._matches(rule["when"], finding, tags):
                continue
            applied.append(rule["id"])
            confidence += float(rule.get("confidence_delta", 0.0))
            multiplier *= float(rule.get("priority_multiplier", 1.0))
            cap = rule.get("cap_decision")
            if cap and _RANK[decision] > _RANK[RiskDecision(cap)]:
                decision = RiskDecision(cap)
            reasons.append(f"[{rule['id']}] {rule['reason']}")
        confidence = min(0.99, max(0.05, confidence))

        anomaly_score = assessment.score if assessment else None
        if anomaly_score is not None:
            confidence += (1 - confidence) * float(self._policy["anomaly_corroboration_weight"]) * anomaly_score
            if anomaly_score > 0:
                reasons.append(f"Behavioural evidence corroborates the finding (anomaly score {anomaly_score:.2f}).")

        if decision is RiskDecision.AUTO_REMEDIATE and confidence < float(
            self._policy["min_confidence_for_auto_remediation"]
        ):
            decision = RiskDecision.ALERT_AND_LOG
            reasons.append(
                f"Confidence {confidence:.2f} is below the auto-remediation floor "
                f"({self._policy['min_confidence_for_auto_remediation']}); a human decides."
            )

        sev_weight = float(self._policy["severity_weights"][finding.severity.value])
        bonus = float(self._policy["anomaly_priority_bonus"]) * (anomaly_score or 0.0)
        priority = sev_weight * confidence * multiplier + bonus
        escalate = bool(
            anomaly_score is not None
            and anomaly_score >= float(self._policy["anomaly_escalation_threshold"])
            and decision is not RiskDecision.AUTO_REMEDIATE
        )
        if escalate:
            reasons.append("Anomalous change that ASPARe will not fix automatically: escalate to a human now.")

        return FusionResult(
            finding_id=finding.finding_id,
            resource_id=finding.resource_id,
            rule_id=finding.rule_id,
            actor=event.actor if event else None,
            confidence=confidence,
            priority=priority,
            original_decision=original,
            adjusted_decision=decision,
            escalate=escalate,
            reasons=reasons,
            rules_applied=applied,
            anomaly=assessment.to_dict() if assessment else {},
        )

    def correlate(self, results: list[FusionResult]) -> list[Incident]:
        """Group related findings into incidents so a human triages one story instead of many alerts."""
        incidents: list[Incident] = []
        by_resource: dict[str, list[FusionResult]] = defaultdict(list)
        for item in results:
            by_resource[item.resource_id].append(item)
        for resource, items in by_resource.items():
            rules = {i.rule_id for i in items}
            ids = [i.finding_id for i in items]
            if {"S3_PUBLIC_ACCESS", "S3_PUBLIC_ACL_EXPOSURE"} <= rules:
                incidents.append(
                    Incident(
                        f"inc-{resource}-exposure",
                        "public-exposure-chain",
                        resource,
                        "CRITICAL",
                        ids,
                        "The Public Access Block is open and a public ACL grant exists: data is reachable by anyone.",
                    )
                )
            elif len(items) >= 3:
                incidents.append(
                    Incident(
                        f"inc-{resource}-compound",
                        "compound-misconfiguration",
                        resource,
                        "HIGH",
                        ids,
                        f"{len(items)} independent weaknesses on one bucket; likely new or neglected.",
                    )
                )
        by_actor: dict[str, set[str]] = defaultdict(set)
        actor_findings: dict[str, list[str]] = defaultdict(list)
        for item in results:
            score = (item.anomaly or {}).get("score")
            if item.actor and score is not None and score >= 0.5:
                by_actor[item.actor].add(item.resource_id)
                actor_findings[item.actor].append(item.finding_id)
        for actor, buckets in by_actor.items():
            if len(buckets) >= 3:
                incidents.append(
                    Incident(
                        f"inc-actor-{abs(hash(actor)) % 10**8}",
                        "actor-campaign",
                        "*",
                        "CRITICAL",
                        actor_findings[actor],
                        f"{actor} caused anomalous changes on {len(buckets)} buckets: possible credential misuse.",
                    )
                )
        return incidents

    # --- context matching -------------------------------------------------------------------------------------
    def _matches(self, when: dict[str, Any], finding: Finding, tags: dict[str, str]) -> bool:
        if "rules" in when and finding.rule_id not in when["rules"]:
            return False
        for key, allowed in (when.get("tags") or {}).items():
            if tags.get(key) not in allowed:
                return False
        for key, needles in (when.get("tag_contains") or {}).items():
            value = (tags.get(key) or "").lower()
            if not any(needle in value for needle in needles):
                return False
        if when.get("tags_any_sensitive"):
            if tags.get("DataClass") not in set(self._context["sensitive_data_classes"]):
                return False
        return True
