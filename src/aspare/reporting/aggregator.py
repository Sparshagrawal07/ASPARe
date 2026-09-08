"""Fold immutable audit records into dashboard summaries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from aspare.core.enums import AuditAction, Severity
from aspare.core.models import AuditRecord


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


@dataclass
class ActivityRow:
    resource: str
    issue: str
    action: str
    result: str
    verified: str
    timestamp: str


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
                    },
                )
                if record.action == AuditAction.FINDING_DETECTED.value:
                    row["detected_at"] = record.timestamp.isoformat()
                    row["status"] = "DETECTED"
                elif record.action == AuditAction.RISK_EVALUATED.value:
                    row["status"] = record.result
                elif record.action == AuditAction.REMEDIATION_EXECUTED.value:
                    row["remediation"] = record.details.get("action_id") or record.result
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
            )
            for item in findings.values()
        ]
        counts = defaultdict(int)
        for row in finding_rows:
            counts[row.severity] += 1
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
