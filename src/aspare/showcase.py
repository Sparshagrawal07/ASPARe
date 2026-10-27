"""Live showcase: break a throwaway bucket on purpose, then stream ASPARe fixing it step by step.

Every scenario creates its own ``aspare-showcase-*`` bucket (tagged ``ASPAReDemo=true``), applies a
realistic misconfiguration, then drives the real detection → risk → remediation → verification → audit
pipeline against it. Nothing outside that bucket is ever touched.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from typing import Any

from aspare.audit.repository import build_record
from aspare.core.enums import AuditAction, RiskDecision
from aspare.core.models import Finding, RemediationOutcome
from aspare.live import LiveSession
from aspare.remediation.engine import safe_remediation_order
from aspare.reporting.explainers import explainer_for, posture_lines
from aspare.runtime import Runtime, build_runtime
from aspare.s3.https_policy import secure_transport_statement

BUCKET_PREFIX = "aspare-showcase-"
_PAB_OFF = {
    "BlockPublicAcls": False,
    "IgnorePublicAcls": False,
    "BlockPublicPolicy": False,
    "RestrictPublicBuckets": False,
}


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    tagline: str
    story: str
    breaks: tuple[str, ...]  # human-readable API calls shown to the audience
    apply: Callable[[Any, str], None]
    expect: tuple[str, ...]  # rule ids the audience should see
    secure_transport: bool = True  # baseline already denies plain HTTP


def _public_read_policy(bucket: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "OopsPublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/*",
                }
            ],
        }
    )


def _break_public(client: Any, bucket: str) -> None:
    client.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration=_PAB_OFF)


def _break_public_policy(client: Any, bucket: str) -> None:
    _break_public(client, bucket)
    client.put_bucket_policy(Bucket=bucket, Policy=_public_read_policy(bucket))


def _break_noop(client: Any, bucket: str) -> None:
    """The bucket is left as AWS creates it: protected from public access, but with no HTTPS rule or versioning."""


SCENARIOS: dict[str, Scenario] = {
    "public": Scenario(
        key="public",
        title="Public Access Block switched off",
        tagline="A rushed engineer disables the safety net.",
        story="Someone turns off all four Public Access Block switches 'just to test something'. "
        "The bucket can now be exposed with a single ACL or policy change.",
        breaks=("PutPublicAccessBlock (all four flags = false)",),
        apply=_break_public,
        expect=("S3_PUBLIC_ACCESS",),
    ),
    "public-policy": Scenario(
        key="public-policy",
        title="Bucket opened to the whole internet",
        tagline="The classic data-leak: a public-read policy.",
        story="The Public Access Block is removed and a bucket policy grants s3:GetObject to Principal '*'. "
        "This is how student records and backups end up on the front page.",
        breaks=("PutPublicAccessBlock (all four flags = false)", "PutBucketPolicy (Allow * s3:GetObject)"),
        apply=_break_public_policy,
        expect=("S3_PUBLIC_ACCESS", "S3_HTTPS_ENFORCEMENT_MISSING"),
        secure_transport=False,
    ),
    "transport": Scenario(
        key="transport",
        title="Plain-HTTP access allowed",
        tagline="Data in transit can be read by anyone on the path.",
        story="A brand new bucket has no policy forcing TLS. Clients can still connect over plain HTTP and "
        "credentials or data can be sniffed on the network.",
        breaks=("(fresh bucket, no aws:SecureTransport deny)",),
        apply=_break_noop,
        expect=("S3_HTTPS_ENFORCEMENT_MISSING",),
        secure_transport=False,
    ),
    "versioning": Scenario(
        key="versioning",
        title="No versioning (human decision)",
        tagline="Some fixes should wait for a person.",
        story="Versioning is off, so an accidental or malicious delete is permanent. It is MEDIUM severity: "
        "ASPARe alerts and waits for your approval instead of acting on its own.",
        breaks=("(fresh bucket, versioning never enabled)",),
        apply=_break_noop,
        expect=("S3_VERSIONING_DISABLED",),
    ),
    "storm": Scenario(
        key="storm",
        title="Perfect storm",
        tagline="Everything wrong at once.",
        story="Public access open, a public-read policy, no TLS rule and no versioning. Watch ASPARe triage the "
        "CRITICAL and HIGH findings automatically and hold the MEDIUM one for approval.",
        breaks=("PutPublicAccessBlock (all four flags = false)", "PutBucketPolicy (Allow * s3:GetObject)"),
        apply=_break_public_policy,
        expect=("S3_PUBLIC_ACCESS", "S3_HTTPS_ENFORCEMENT_MISSING", "S3_VERSIONING_DISABLED"),
        secure_transport=False,
    ),
}


@dataclass
class ShowcaseEvent:
    stage: str  # provision | misconfigure | detect | classify | remediate | verify | audit | done
    title: str
    status: str  # ok | warn | fail | info
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ShowcaseState:
    bucket: str
    runtime: Runtime
    findings: list[Finding] = field(default_factory=list)
    outcomes: list[RemediationOutcome] = field(default_factory=list)


def _runtime_for(session: LiveSession, bucket: str) -> Runtime:
    settings = replace(
        session.runtime.settings,
        allowed_buckets=frozenset({bucket}),
        require_demo_tag=True,
        dry_run=False,
        alert_topic_arn=None,
    )
    return build_runtime(settings, client=session.client)


def _create_bucket(session: LiveSession, name: str, secure_transport: bool) -> None:
    region = session.runtime.settings.region
    if region == "us-east-1":
        session.client.create_bucket(Bucket=name)
    else:
        session.client.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": region})
    session.client.put_bucket_tagging(
        Bucket=name, Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}, {"Key": "Showcase", "Value": "true"}]}
    )
    # Secure baseline, so each scenario shows only its own misconfiguration.
    session.client.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={k: True for k in _PAB_OFF})
    session.client.put_bucket_encryption(
        Bucket=name,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    if secure_transport:
        session.client.put_bucket_policy(
            Bucket=name,
            Policy=json.dumps({"Version": "2012-10-17", "Statement": [secure_transport_statement(name)]}),
        )


def reasoning_for(finding: Finding) -> str:
    """Plain-language justification of the risk decision, taken from the active risk policy."""
    decision = finding.decision
    sev = finding.severity.value
    if decision is RiskDecision.AUTO_REMEDIATE:
        return (
            f"{sev} is in the policy's auto-remediate tier and the fix ({finding.remediation_action}) is a reviewed, "
            "reversible, allow-listed action, so ASPARe acts immediately and verifies the result."
        )
    if decision is RiskDecision.ALERT_AND_LOG:
        return (
            f"{sev} is in the alert tier: the change is low-risk to leave for a short time but important, so ASPARe "
            "records it, notifies a human and waits for approval before changing anything."
        )
    if decision is RiskDecision.MANUAL_REVIEW:
        return "No safe automatic fix exists for this control, so it is routed to manual review."
    return f"{sev} is informational; it is logged for the audit trail only."


def run_scenario(
    session: LiveSession, scenario: Scenario, autonomous: bool = True
) -> Iterator[ShowcaseEvent | ShowcaseState]:
    """Yield ShowcaseEvent items live; the last item yielded is the final ShowcaseState."""
    bucket = f"{BUCKET_PREFIX}{scenario.key}-{uuid.uuid4().hex[:6]}"
    yield ShowcaseEvent(
        "provision", "Creating a throwaway bucket", "info", f"`{bucket}` in {session.runtime.settings.region}"
    )
    _create_bucket(session, bucket, scenario.secure_transport)
    runtime = _runtime_for(session, bucket)
    state = ShowcaseState(bucket=bucket, runtime=runtime)
    yield ShowcaseEvent(
        "provision",
        "Bucket ready",
        "ok",
        "Starts from a secure baseline and is tagged `ASPAReDemo=true`, the only kind of bucket ASPARe may modify.",
        {"bucket": bucket},
    )

    scenario.apply(session.client, bucket)
    yield ShowcaseEvent(
        "misconfigure",
        "Misconfiguration applied to real AWS",
        "warn",
        scenario.story,
        {"api_calls": list(scenario.breaks)},
    )

    outcome = runtime.detection_workflow.run_raw(
        {
            "source": "aspare.direct",
            "detail": {"bucket": bucket, "region": runtime.settings.region, "actor": "showcase"},
        }
    )
    published = getattr(runtime.publisher, "published", None)
    if published is not None:
        published.clear()
    state.findings = list(outcome.findings)
    resource = outcome.resources[0] if outcome.resources else None
    yield ShowcaseEvent(
        "detect",
        f"Inspected the bucket: {len(state.findings)} finding(s)",
        "fail" if state.findings else "ok",
        "ASPARe read the live configuration (7 read-only S3 APIs) and ran every rule in the policy knowledge base.",
        {"snapshot": posture_lines(resource.snapshot()) if resource else []},
    )

    for finding in state.findings:
        expl = explainer_for(finding.rule_id)
        yield ShowcaseEvent(
            "classify",
            f"{finding.severity.value} · {expl['title']}",
            "fail" if finding.severity.value in {"CRITICAL", "HIGH"} else "warn",
            expl["what"],
            {
                "rule": finding.rule_id,
                "why_it_matters": expl["affects"],
                "decision": finding.decision.value if finding.decision else "n/a",
                "reasoning": reasoning_for(finding),
                "standards": expl.get("standards") or [],
            },
        )

    auto = safe_remediation_order([f for f in state.findings if f.decision is RiskDecision.AUTO_REMEDIATE])
    if not autonomous:
        yield ShowcaseEvent(
            "remediate", "Human-approval mode", "info", "Nothing is changed until you approve each finding below."
        )
    else:
        for finding in auto:
            expl = explainer_for(finding.rule_id)
            yield ShowcaseEvent(
                "remediate", f"Applying: {expl['remedy_name']}", "info", expl["remedy_does"], {"rule": finding.rule_id}
            )
            result = runtime.remediation_workflow.run(finding)
            state.outcomes.append(result)
            yield _verification_event(result)

    yield ShowcaseEvent(
        "audit",
        "Audit trail written",
        "ok",
        f"{len(runtime.audit.list_records()) if hasattr(runtime.audit, 'list_records') else 'All'} record(s) in "
        f"`{session.audit_path}` capture detection, risk decision, action and verification.",
    )
    yield state


def _verification_event(result: RemediationOutcome) -> ShowcaseEvent:
    ver = result.verification
    return ShowcaseEvent(
        "verify",
        "Verified: fix confirmed by re-inspection" if ver.verified else "Not verified",
        "ok" if ver.verified else "fail",
        ver.message,
        {
            "before": posture_lines(ver.before_state),
            "after": posture_lines(ver.after_state),
            "action": result.action_result.action_id,
            "rule": result.finding.rule_id,
        },
    )


def approve_pending(session: LiveSession, state: ShowcaseState, finding: Finding, approver: str) -> ShowcaseEvent:
    """Human approval for a held finding: audit the approval, remediate, verify."""
    state.runtime.audit.append(
        build_record(
            action=AuditAction.REMEDIATION_APPROVED.value,
            result="APPROVED",
            resource_id=finding.resource_id,
            correlation_id=finding.correlation_id,
            finding=finding,
            actor=approver,
            details={"action": finding.remediation_action},
        )
    )
    result = state.runtime.remediation_workflow.run(finding)
    state.outcomes.append(result)
    return _verification_event(result)


def pending_findings(state: ShowcaseState) -> list[Finding]:
    done = {o.finding.finding_id for o in state.outcomes}
    return [
        f for f in state.findings if f.finding_id not in done and state.runtime.remediation_workflow.can_remediate(f)
    ]


def cleanup_bucket(session: LiveSession, bucket: str) -> None:
    """Delete a showcase bucket created by this module (refuses anything else)."""
    if not bucket.startswith(BUCKET_PREFIX):
        raise ValueError("Refusing to delete a bucket that is not a showcase bucket")
    client = session.client
    for call in (client.delete_bucket_policy,):
        try:
            call(Bucket=bucket)
        except Exception:  # noqa: BLE001
            pass
    client.delete_bucket(Bucket=bucket)


def list_showcase_buckets(session: LiveSession) -> list[str]:
    names = [b["Name"] for b in session.client.list_buckets().get("Buckets", [])]
    return [n for n in names if n.startswith(BUCKET_PREFIX)]
