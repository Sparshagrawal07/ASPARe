"""Live AWS session: read-only scan of a real account with human-approved remediation.

Detection never writes. A finding is only remediated when an operator approves it, and the
SafetyGate (allowlist + ``ASPAReDemo=true`` tag by default) still applies to every write.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from aspare.audit.repository import build_record
from aspare.config.settings import Settings
from aspare.core.enums import AuditAction
from aspare.core.models import Finding, RemediationOutcome
from aspare.runtime import Runtime, build_runtime

DEFAULT_LIVE_AUDIT = "var/audit/live.jsonl"


class LiveConnectionError(RuntimeError):
    """Raised when AWS credentials are missing or rejected."""


@dataclass
class LiveSession:
    runtime: Runtime
    client: Any
    identity: dict[str, str]
    audit_path: str
    inventory: dict[str, Any] = field(default_factory=lambda: {"buckets": []})
    findings: list[Finding] = field(default_factory=list)


def settings_for_live(region: str, dry_run: bool, audit_path: str = DEFAULT_LIVE_AUDIT) -> Settings:
    """Environment settings with live-safe overrides: local audit file, no event bus, optional dry-run."""
    return replace(
        Settings.from_env(),
        region=region,
        dry_run=dry_run,
        audit_backend="jsonl",
        audit_path=Path(audit_path),
        event_bus_name=None,
    )


def connect(region: str = "us-east-1", profile: str | None = None, dry_run: bool = True) -> LiveSession:
    """Validate credentials with STS and build a runtime bound to the real account."""
    session = boto3.Session(profile_name=profile or None, region_name=region)
    try:
        who = session.client("sts").get_caller_identity()
    except (BotoCoreError, ClientError) as exc:
        raise LiveConnectionError(
            "AWS credentials are missing or invalid. Run `aws configure` (or `aws sso login`) "
            f"and retry. Details: {exc}"
        ) from exc
    client = session.client("s3", region_name=region)
    audit_path = os.environ.get("ASPARE_LIVE_AUDIT_PATH", DEFAULT_LIVE_AUDIT)
    Path(audit_path).parent.mkdir(parents=True, exist_ok=True)
    runtime = build_runtime(settings_for_live(region, dry_run, audit_path), client=client)
    return LiveSession(
        runtime=runtime,
        client=client,
        identity={"account": str(who.get("Account", "")), "arn": str(who.get("Arn", ""))},
        audit_path=audit_path,
    )


def scan(session: LiveSession) -> list[Finding]:
    """Read-only inventory scan of every bucket (restricted to the allowlist if one is set)."""
    outcome = session.runtime.detection_workflow.run_raw(
        {
            "source": "aspare.scheduler",
            "detail-type": "Scheduled Event",
            "detail": {"region": session.runtime.settings.region, "actor": "aspare.dashboard"},
        }
    )
    published = getattr(session.runtime.publisher, "published", None)
    if published is not None:
        published.clear()  # nothing is remediated without explicit approval
    session.inventory = {
        "source": f"Live AWS account {session.identity.get('account', '?')}",
        "buckets": [{"name": item.resource_id, "tags": dict(item.tags)} for item in outcome.resources],
    }
    session.findings = list(outcome.findings)
    return session.findings


def approval_gate(session: LiveSession, finding: Finding) -> tuple[bool, str]:
    """Whether an operator may approve this finding, and why not if blocked."""
    settings = session.runtime.settings
    tags = next(((b.get("tags") or {}) for b in session.inventory["buckets"] if b["name"] == finding.resource_id), {})
    if not settings.is_bucket_allowed(finding.resource_id, tags):
        return False, (
            f"Safety gate: bucket must be in ASPARE_ALLOWED_BUCKETS and tagged "
            f"{settings.demo_tag_key}={settings.demo_tag_value}."
        )
    if not session.runtime.remediation_workflow.can_remediate(finding):
        return False, "No automated remediation exists for this control; fix it manually."
    return True, ""


def approve(session: LiveSession, finding: Finding, approver: str = "dashboard-operator") -> RemediationOutcome | None:
    """Record the approval, then remediate + verify. Returns ``None`` in dry-run (nothing is written)."""
    dry_run = session.runtime.settings.dry_run
    session.runtime.audit.append(
        build_record(
            action=AuditAction.REMEDIATION_APPROVED.value,
            result="DRY_RUN" if dry_run else "APPROVED",
            resource_id=finding.resource_id,
            correlation_id=finding.correlation_id,
            finding=finding,
            actor=approver,
            details={"dry_run": dry_run, "action": finding.remediation_action},
        )
    )
    if dry_run:
        return None
    return session.runtime.remediation_workflow.run(finding)
