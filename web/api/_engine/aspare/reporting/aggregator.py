"""Fold immutable audit records into dashboard summaries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from aspare.core.enums import AuditAction, Severity
from aspare.core.models import AuditRecord

# Dashboard-facing, read-only extensions (additive: existing classes/methods untouched).

SENSITIVE_CLASSES = frozenset({"FERPA", "PHI", "FINANCIAL", "PII", "SECRETS"})
SENSITIVE_ORDER = ["FERPA", "PHI", "FINANCIAL", "PII", "SECRETS"]


@dataclass
class HumanImpactEntry:
    hue_hex: str
    impact_statement: str
    sensitive: bool


# Static human-impact map keyed by DataClass (api-contract.md §3).
HUMAN_IMPACT_MAP: dict[str, HumanImpactEntry] = {
    "FERPA": HumanImpactEntry(
        "#60a5fa", "Protecting student transcripts, enrollment, and financial-aid records.", True
    ),
    "PHI": HumanImpactEntry("#fb7185", "Protecting patient clinic visits and consent records.", True),
    "FINANCIAL": HumanImpactEntry("#f59e0b", "Protecting payroll and tax batch records.", True),
    "PII": HumanImpactEntry("#a78bfa", "Protecting student IDs, HR, and housing records.", True),
    "SECRETS": HumanImpactEntry("#c084fc", "Protecting infrastructure credentials and deployment artifacts.", True),
    "AUDIT": HumanImpactEntry("#94a3b8", "Protecting CloudTrail and security audit trails.", False),
    "BACKUP": HumanImpactEntry("#2dd4bf", "Protecting database snapshots and home-directory backups.", False),
    "LEGAL": HumanImpactEntry("#6366f1", "Protecting legal holds and e-discovery material.", False),
    "SENSITIVE": HumanImpactEntry("#fb923c", "Protecting quarantined and classified findings.", False),
    "INTERNAL": HumanImpactEntry("#22d3ee", "Protecting internal analytics and CI artifacts.", False),
    "PUBLIC": HumanImpactEntry("#4ade80", "Protecting public-facing marketing and media assets.", False),
}


@dataclass
class SeverityDistribution:
    critical: int
    high: int
    medium: int
    low: int
    total: int


@dataclass
class DataClassBucket:
    data_class: str
    bucket_count: int
    protected_count: int
    exposed_count: int
    hue_hex: str
    impact_statement: str


@dataclass
class DataClassBreakdown:
    classes: list[DataClassBucket]
    total_buckets: int
    total_sensitive_buckets: int
    total_protected_sensitive: int


@dataclass
class RemediationOutcome:
    successful: int
    failed: int
    total: int
    success_rate_pct: float


@dataclass
class PipelineStage:
    key: str
    label: str
    description: str
    status: str
    order: int


@dataclass
class HumanImpactSummary:
    protected_classes: list[DataClassBucket]
    one_line_narrative: str


@dataclass
class FindingRow:
    resource: str
    rule: str
    severity: str
    status: str
    detected_at: str
    remediation: str
    verification: str
    finding_id: str
    remedy_message: str = ""
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityRow:
    resource: str
    issue: str
    action: str
    result: str
    verified: str
    timestamp: str
    message: str = ""
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardSnapshot:
    resources_scanned: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    successful_remediations: int
    failed_remediations: int
    findings: list[FindingRow] = field(default_factory=list)
    activity: list[ActivityRow] = field(default_factory=list)


class ReportingAggregator:
    def summarize(self, records: list[AuditRecord]) -> DashboardSnapshot:
        scanned: set[str] = set()
        findings: dict[str, dict[str, Any]] = {}
        activity: list[ActivityRow] = []
        success = 0
        failed = 0

        for record in sorted(records, key=lambda item: item.timestamp):
            if record.action == AuditAction.SCAN_COMPLETED.value:
                details = record.details or {}
                ids = details.get("resources_scanned") or [record.resource_id]
                for item in ids:
                    if item and item != "*":
                        scanned.add(item)
            if record.finding_id:
                row = findings.setdefault(
                    record.finding_id,
                    {
                        "resource": record.resource_id,
                        "rule": record.rule_id or "",
                        "severity": record.severity.value if record.severity else "",
                        "status": record.result,
                        "detected_at": record.timestamp.isoformat(),
                        "remediation": "",
                        "verification": "",
                        "finding_id": record.finding_id,
                        "remedy_message": "",
                        "before_state": {},
                        "after_state": {},
                    },
                )
                if record.before_state:
                    row["before_state"] = record.before_state
                if record.after_state:
                    row["after_state"] = record.after_state
                if record.action == AuditAction.FINDING_DETECTED.value:
                    row["detected_at"] = record.timestamp.isoformat()
                    row["status"] = "DETECTED"
                elif record.action == AuditAction.RISK_EVALUATED.value:
                    row["status"] = record.result
                elif record.action == AuditAction.REMEDIATION_EXECUTED.value:
                    row["remediation"] = record.details.get("action_id") or record.result
                    row["remedy_message"] = str(record.details.get("message") or "")
                    row["status"] = record.result
                elif record.action == AuditAction.VERIFICATION_COMPLETED.value:
                    row["verification"] = record.result
                    row["status"] = "REMEDIATED" if record.verified else "REMEDIATION_FAILED"
                    if record.verified:
                        success += 1
                    else:
                        failed += 1
                    activity.append(
                        ActivityRow(
                            resource=record.resource_id,
                            issue=record.rule_id or "",
                            action=row.get("remediation") or record.action,
                            result=record.result,
                            verified="yes" if record.verified else "no",
                            timestamp=record.timestamp.isoformat(),
                            message=str(row.get("remedy_message") or record.details.get("message") or ""),
                            before_state=row.get("before_state") or {},
                            after_state=record.after_state or row.get("after_state") or {},
                        )
                    )

        finding_rows = [
            FindingRow(
                resource=item["resource"],
                rule=item["rule"],
                severity=item["severity"],
                status=item["status"],
                detected_at=item["detected_at"],
                remediation=item["remediation"] or "none",
                verification=item["verification"] or "n/a",
                finding_id=item["finding_id"],
                remedy_message=str(item.get("remedy_message") or ""),
                before_state=dict(item.get("before_state") or {}),
                after_state=dict(item.get("after_state") or {}),
            )
            for item in findings.values()
        ]
        counts: dict[str, int] = defaultdict(int)
        for item_row in finding_rows:
            counts[item_row.severity] += 1
        return DashboardSnapshot(
            resources_scanned=len(scanned),
            total_findings=len(finding_rows),
            critical_findings=counts[Severity.CRITICAL.value],
            high_findings=counts[Severity.HIGH.value],
            medium_findings=counts[Severity.MEDIUM.value],
            successful_remediations=success,
            failed_remediations=failed,
            findings=sorted(finding_rows, key=lambda item: item.detected_at, reverse=True),
            activity=sorted(activity, key=lambda item: item.timestamp, reverse=True),
        )

    @staticmethod
    def severity_distribution(snapshot: DashboardSnapshot) -> SeverityDistribution:
        counts: dict[str, int] = defaultdict(int)
        for row in snapshot.findings:
            counts[row.severity] += 1
        critical = counts[Severity.CRITICAL.value]
        high = counts[Severity.HIGH.value]
        medium = counts[Severity.MEDIUM.value]
        low = counts[Severity.LOW.value]
        return SeverityDistribution(
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            total=critical + high + medium + low,
        )

    @staticmethod
    def remediation_outcome(snapshot: DashboardSnapshot) -> RemediationOutcome:
        successful = snapshot.successful_remediations
        failed = snapshot.failed_remediations
        total = successful + failed
        rate = round(successful / total * 100) if total > 0 else 0
        return RemediationOutcome(
            successful=successful,
            failed=failed,
            total=total,
            success_rate_pct=rate,
        )

    @staticmethod
    def data_class_breakdown(inventory: Any, snapshot: DashboardSnapshot) -> DataClassBreakdown:
        buckets = inventory.get("buckets", []) if isinstance(inventory, dict) else list(inventory or [])
        risky = {
            row.resource for row in snapshot.findings if row.severity in {Severity.CRITICAL.value, Severity.HIGH.value}
        }
        grouped: dict[str, list[Any]] = defaultdict(list)
        for bucket in buckets:
            tags = bucket.get("tags") or {}
            data_class = tags.get("DataClass")
            if data_class:
                grouped[data_class].append(bucket)

        order_index = {name: index for index, name in enumerate(SENSITIVE_ORDER)}

        def sort_key(data_class: str) -> tuple[int, int | str, int]:
            count = len(grouped[data_class])
            if data_class in order_index:
                return (0, order_index[data_class], -count)
            return (1, data_class, -count)

        entry_for = HUMAN_IMPACT_MAP.get
        classes: list[DataClassBucket] = []
        for data_class in sorted(grouped, key=sort_key):
            bucket_list = grouped[data_class]
            bucket_count = len(bucket_list)
            protected_count = sum(1 for bucket in bucket_list if bucket.get("name") not in risky)
            entry = entry_for(data_class) or HumanImpactEntry("#94a3b8", "", False)
            classes.append(
                DataClassBucket(
                    data_class=data_class,
                    bucket_count=bucket_count,
                    protected_count=protected_count,
                    exposed_count=bucket_count - protected_count,
                    hue_hex=entry.hue_hex,
                    impact_statement=entry.impact_statement,
                )
            )

        total_buckets = sum(bucket.bucket_count for bucket in classes)
        total_sensitive_buckets = sum(
            bucket.bucket_count for bucket in classes if bucket.data_class in SENSITIVE_CLASSES
        )
        total_protected_sensitive = sum(
            bucket.protected_count for bucket in classes if bucket.data_class in SENSITIVE_CLASSES
        )
        return DataClassBreakdown(
            classes=classes,
            total_buckets=total_buckets,
            total_sensitive_buckets=total_sensitive_buckets,
            total_protected_sensitive=total_protected_sensitive,
        )

    @staticmethod
    def human_impact_summary(breakdown: DataClassBreakdown) -> HumanImpactSummary:
        protected = [
            bucket for bucket in breakdown.classes if bucket.data_class in SENSITIVE_CLASSES and bucket.bucket_count > 0
        ][:5]
        total = sum(bucket.bucket_count for bucket in protected)
        if not protected:
            narrative = "No sensitive-class buckets in the estate."
        elif len(protected) == 1:
            narrative = f"Protecting {protected[0].data_class} across {total} bucket{'s' if total != 1 else ''}."
        else:
            names = ", ".join(bucket.data_class for bucket in protected[:2])
            narrative = f"Protecting {names} across {total} buckets."
        return HumanImpactSummary(protected_classes=protected, one_line_narrative=narrative)

    @staticmethod
    def pipeline_state(session_step: str, has_records: bool) -> list[PipelineStage]:
        stages = [
            PipelineStage("detect", "Detect", "Inspect every bucket against the policy knowledge base.", "pending", 1),
            PipelineStage(
                "classify", "Classify", "Map findings to CRITICAL / HIGH / MEDIUM risk decisions.", "pending", 2
            ),
            PipelineStage("remediate", "Remediate", "Auto-apply approved fixes (CRITICAL/HIGH only).", "pending", 3),
            PipelineStage(
                "verify", "Verify", "Re-inspect after each write — a Put* response is not success.", "pending", 4
            ),
            PipelineStage("audit", "Audit", "Record every action to the immutable audit trail.", "pending", 5),
        ]
        complete = {
            "detect": session_step in {"detected", "remediated"},
            "classify": session_step in {"detected", "remediated"},
            "remediate": session_step == "remediated",
            "verify": session_step == "remediated",
            "audit": bool(has_records),
        }
        active_for = {"idle": "detect", "loaded": "detect", "detected": "remediate"}
        for stage in stages:
            if complete[stage.key]:
                stage.status = "complete"
            elif stage.key == active_for.get(session_step):
                stage.status = "active"
            else:
                stage.status = "pending"
        return stages

    @staticmethod
    def data_class_for_resource(resource: str, inventory: Any) -> str | None:
        buckets = inventory.get("buckets", []) if isinstance(inventory, dict) else list(inventory or [])
        for bucket in buckets:
            if bucket.get("name") == resource:
                return (bucket.get("tags") or {}).get("DataClass")
        return None
