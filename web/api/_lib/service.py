"""ASPARe web service: run the real engine over a simulated estate, statelessly.

Every request carries the whole estate (a handful of small resources), so the serverless functions hold no state and
visitors cannot affect each other. No cloud credentials are accepted or used anywhere.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ENGINE_DIR = Path(__file__).resolve().parents[1] / "_engine"
os.environ.setdefault("ASPARE_ROOT", str(ENGINE_DIR))
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from aspare.config.settings import Settings  # noqa: E402
from aspare.core.enums import EventType, RiskDecision  # noqa: E402
from aspare.core.ids import correlation_id  # noqa: E402
from aspare.core.models import Finding, StorageEvent  # noqa: E402
from aspare.intelligence.fusion import FusionResult  # noqa: E402
from aspare.intelligence.reasoner import OfflineReasoner  # noqa: E402
from aspare.policygen import generate_policies, validate_least_privilege  # noqa: E402
from aspare.providers.routing import identity_for  # noqa: E402
from aspare.providers.simulated import FakeAzureApi, FakeGcsApi, FakeS3Client  # noqa: E402
from aspare.remediation.engine import safe_remediation_order  # noqa: E402
from aspare.reporting.explainers import explainer_for, posture_lines  # noqa: E402
from aspare.runtime import Runtime, build_runtime  # noqa: E402
from aspare.s3.https_policy import PUBLIC_ACL_URIS, has_secure_transport_deny  # noqa: E402

CLOUDS = ("aws", "azure", "gcp")
CONTROLS = ("publicBlocked", "encrypted", "versioning", "https", "publicGrant")
_NAME = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$")
_PAB_CHANGES = {"PutBucketPublicAccessBlock", "DeletePublicAccessBlock"}
MAX_RESOURCES = 20


class ValidationError(ValueError):
    pass


def default_estate() -> dict[str, Any]:
    def res(cloud: str, name: str, tags: dict[str, str], **controls: bool | None) -> dict[str, Any]:
        base = {"publicBlocked": True, "encrypted": True, "versioning": True, "https": True, "publicGrant": False}
        base.update(controls)
        return {"cloud": cloud, "name": name, "tags": {"ASPAReDemo": "true", **tags}, "controls": base}

    return {
        "resources": [
            res(
                "aws",
                "ferpa-transcripts-prod",
                {"DataClass": "FERPA", "Environment": "prod"},
                publicBlocked=False,
                versioning=False,
                https=False,
            ),
            res(
                "aws",
                "campus-marketing-site",
                {"DataClass": "PUBLIC", "Purpose": "marketing", "Environment": "prod"},
                publicBlocked=False,
                publicGrant=True,
            ),
            res(
                "aws",
                "ci-build-cache",
                {"DataClass": "INTERNAL", "Purpose": "ci-cache", "Environment": "dev"},
                versioning=False,
            ),
            res("aws", "payroll-archive", {"DataClass": "FINANCIAL", "Environment": "prod"}),
            res(
                "azure",
                "studentportalprod",
                {"DataClass": "PII", "Environment": "prod"},
                publicBlocked=False,
                https=False,
                publicGrant=True,
                versioning=False,
            ),
            res(
                "gcp",
                "research-irb-consents",
                {"DataClass": "PHI", "Environment": "prod"},
                publicBlocked=False,
                publicGrant=True,
                versioning=False,
                https=None,
            ),
            res(
                "gcp",
                "ml-scratch-bucket",
                {"DataClass": "INTERNAL", "Purpose": "scratch", "Environment": "dev"},
                versioning=False,
                https=None,
            ),
        ],
        "changes": [
            {
                "resource": "ferpa-transcripts-prod",
                "actor": "arn:aws:iam::123456789012:root",
                "eventName": "PutBucketPublicAccessBlock",
                "hour": 3,
                "minute": 0,
            },
            {
                "resource": "studentportalprod",
                "actor": "arn:aws:iam::123456789012:root",
                "eventName": "PutBucketPublicAccessBlock",
                "hour": 3,
                "minute": 4,
            },
            {
                "resource": "research-irb-consents",
                "actor": "arn:aws:iam::123456789012:root",
                "eventName": "PutBucketPublicAccessBlock",
                "hour": 3,
                "minute": 9,
            },
        ],
    }


# --- validation --------------------------------------------------------------------------------------------------
def validate_estate(estate: Any) -> dict[str, Any]:
    if not isinstance(estate, dict) or not isinstance(estate.get("resources"), list):
        raise ValidationError("estate.resources must be a list")
    resources = estate["resources"]
    if not 1 <= len(resources) <= MAX_RESOURCES:
        raise ValidationError(f"estate must contain 1-{MAX_RESOURCES} resources")
    seen: set[str] = set()
    clean: list[dict[str, Any]] = []
    for item in resources:
        if not isinstance(item, dict):
            raise ValidationError("each resource must be an object")
        cloud, name = item.get("cloud"), item.get("name")
        if cloud not in CLOUDS:
            raise ValidationError(f"cloud must be one of {CLOUDS}")
        if not isinstance(name, str) or not _NAME.match(name):
            raise ValidationError("resource names must be 3-63 chars: lowercase letters, digits, dots, hyphens")
        if name in seen:
            raise ValidationError(f"duplicate resource {name}")
        seen.add(name)
        tags = item.get("tags") or {}
        if not isinstance(tags, dict) or len(tags) > 10:
            raise ValidationError("tags must be an object with at most 10 entries")
        for k, v in tags.items():
            if not (isinstance(k, str) and isinstance(v, str) and len(k) <= 64 and len(v) <= 64):
                raise ValidationError("tag keys and values must be strings of at most 64 characters")
        controls = item.get("controls") or {}
        if not isinstance(controls, dict):
            raise ValidationError("controls must be an object")
        fixed: dict[str, Any] = {}
        for key in CONTROLS:
            value = controls.get(key, True if key != "publicGrant" else False)
            if value is not None and not isinstance(value, bool):
                raise ValidationError(f"control {key} must be true, false or null")
            fixed[key] = value
        clean.append({"cloud": cloud, "name": name, "tags": dict(tags), "controls": fixed})
    changes = estate.get("changes") or []
    if not isinstance(changes, list) or len(changes) > 20:
        raise ValidationError("changes must be a list of at most 20 entries")
    clean_changes = []
    for c in changes:
        if not (isinstance(c, dict) and c.get("resource") in seen and isinstance(c.get("actor"), str)):
            raise ValidationError("each change needs a known resource and an actor")
        if c.get("eventName") not in {
            "PutBucketPublicAccessBlock",
            "DeletePublicAccessBlock",
            "DeleteBucketEncryption",
            "PutBucketAcl",
            "PutBucketPolicy",
            "PutBucketVersioning",
        }:
            raise ValidationError("unsupported change eventName")
        clean_changes.append(
            {
                "resource": c["resource"],
                "actor": c["actor"][:128],
                "eventName": c["eventName"],
                "hour": int(c.get("hour", 12)) % 24,
                "minute": int(c.get("minute", 0)) % 60,
            }
        )
    return {"resources": clean, "changes": clean_changes}


# --- estate <-> simulated clouds ---------------------------------------------------------------------------------
def resource_id(cloud: str, name: str) -> str:
    return {"aws": name, "azure": f"azure://{name}", "gcp": f"gcs://{name}"}[cloud]


_PAB_OFF = {
    "BlockPublicAcls": False,
    "IgnorePublicAcls": False,
    "BlockPublicPolicy": False,
    "RestrictPublicBuckets": False,
}
_LABEL_KEYS = {"ASPAReDemo": "asparedemo", "DataClass": "dataclass", "Purpose": "purpose", "Environment": "environment"}


def _build_runtime(estate: dict[str, Any]) -> Runtime:
    s3, az, gcs = FakeS3Client(), FakeAzureApi(), FakeGcsApi()
    ids: list[str] = []
    for r in estate["resources"]:
        c, name, tags = r["controls"], r["name"], r["tags"]
        ids.append(resource_id(r["cloud"], name))
        if r["cloud"] == "aws":
            pab = {k: True for k in _PAB_OFF} if c["publicBlocked"] else dict(_PAB_OFF)
            s3.add(
                name,
                tags=tags,
                pab=pab,
                encrypted=bool(c["encrypted"]),
                versioning=bool(c["versioning"]),
                https_policy=bool(c["https"]),
                public_acl=bool(c["publicGrant"]),
            )
        elif r["cloud"] == "azure":
            az.add(
                name,
                tags=tags,
                public=not c["publicBlocked"],
                https_only=bool(c["https"]),
                containers=[{"name": "data", "public_access": "blob" if c["publicGrant"] else "none"}],
            )
            az.versioning[name] = bool(c["versioning"])
        else:
            labels = {_LABEL_KEYS.get(k, k.lower()): v.lower() if k != "ASPAReDemo" else v for k, v in tags.items()}
            gcs.add(
                name,
                labels=labels,
                public_iam=bool(c["publicGrant"]),
                prevention="enforced" if c["publicBlocked"] else "inherited",
                ubla=bool(c["publicBlocked"]),
            )
            gcs.buckets[name]["versioning_enabled"] = bool(c["versioning"])
    settings = replace(
        Settings.from_env(),
        allowed_buckets=frozenset(ids),
        require_demo_tag=True,
        dry_run=False,
        audit_backend="memory",
        event_bus_name=None,
        alert_topic_arn=None,
        fusion_enabled=True,
        region="us-east-1",
    )
    kwargs: dict[str, Any] = {}
    if any(r["cloud"] == "azure" for r in estate["resources"]):
        kwargs["azure_api"] = az
    if any(r["cloud"] == "gcp" for r in estate["resources"]):
        kwargs["gcs_api"] = gcs
    return build_runtime(settings, client=s3, **kwargs)


def _inspect_controls(runtime: Runtime, estate: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in estate["resources"]:
        res = runtime.storage_inspector.inspect(resource_id(r["cloud"], r["name"]))
        https: bool | None
        if res.https_only is not None:
            https = res.https_only
        elif r["cloud"] == "gcp":
            https = None
        else:
            https = has_secure_transport_deny(res.policy.document, res.resource_id)
        out.append(
            {
                **r,
                "controls": {
                    "publicBlocked": res.public_access_block.all_blocked(),
                    "encrypted": res.encryption.enabled,
                    "versioning": res.versioning.is_enabled(),
                    "https": https,
                    "publicGrant": any(g.grantee_uri in PUBLIC_ACL_URIS for g in res.acl.grants),
                },
            }
        )
    return out


def _event_for(change: dict[str, Any], estate: dict[str, Any]) -> StorageEvent:
    res = next(r for r in estate["resources"] if r["name"] == change["resource"])
    rid = resource_id(res["cloud"], res["name"])
    provider, rtype = identity_for(rid)
    params = {"PublicAccessBlockConfiguration": dict(_PAB_OFF)} if change["eventName"] in _PAB_CHANGES else {}
    eid = f"chg-{res['name']}"
    return StorageEvent(
        event_id=eid,
        provider=provider,
        event_type=EventType.CLOUDTRAIL_API_CALL,
        resource_type=rtype,
        resource_id=rid,
        actor=change["actor"],
        timestamp=datetime(2026, 4, 5, change["hour"], change["minute"], tzinfo=UTC),
        region="us-east-1",
        correlation_id=correlation_id(eid),
        metadata={"event_name": change["eventName"], "request_parameters": params},
    )


def _scan(runtime: Runtime, estate: dict[str, Any]) -> list[Finding]:
    by_name = {c["resource"]: c for c in estate["changes"]}
    changed = sorted(estate["changes"], key=lambda c: (c["hour"], c["minute"]))
    findings: list[Finding] = []
    for r in estate["resources"]:  # quiet resources first, so the baseline predates the suspicious changes
        if r["name"] not in by_name:
            rid = resource_id(r["cloud"], r["name"])
            findings += runtime.detection_workflow.run_raw(
                {"source": "aspare.scheduler", "detail": {"buckets": [rid]}}
            ).findings
    for change in changed:
        findings += runtime.detection_workflow.run(_event_for(change, estate)).findings
    published = getattr(runtime.publisher, "published", None)
    if published is not None:
        published.clear()
    return findings


def _cloud_of(finding: Finding) -> str:
    return {"aws": "aws", "azure": "azure", "gcp": "gcp"}[finding.provider.value]


def _finding_payload(runtime: Runtime, f: Finding) -> dict[str, Any]:
    fusion = f.metadata.get("fusion") or {}
    expl = explainer_for(f.rule_id)
    tags = (f.before_state or {}).get("tags") or {}
    analysis = OfflineReasoner().analyze(f, tags)
    return {
        "id": f.finding_id,
        "resource": f.resource_id,
        "cloud": _cloud_of(f),
        "rule": f.rule_id,
        "title": expl["title"],
        "severity": f.severity.value,
        "ruleOnlyDecision": fusion.get("original_decision"),
        "decision": f.decision.value if f.decision else None,
        "confidence": fusion.get("confidence"),
        "priority": fusion.get("priority"),
        "reasons": fusion.get("reasons") or [],
        "contextRules": fusion.get("rules_applied") or [],
        "anomaly": fusion.get("anomaly") or {},
        "escalate": bool(fusion.get("escalate")),
        "what": expl["what"],
        "affects": expl["affects"],
        "remedy": expl["remedy_name"],
        "remedyDoes": expl["remedy_does"],
        "standards": f.metadata.get("standards") or [],
        "analysis": {
            "summary": analysis.summary,
            "rootCause": analysis.root_cause,
            "recommendation": analysis.recommendation,
        },
        "canFix": runtime.remediation_workflow.can_remediate(f),
    }


def run_scan(raw_estate: Any) -> dict[str, Any]:
    estate = validate_estate(raw_estate)
    runtime = _build_runtime(estate)
    findings = _scan(runtime, estate)
    payload = sorted((_finding_payload(runtime, f) for f in findings), key=lambda p: -(p["priority"] or 0))
    results = [FusionResult.from_dict(f.metadata["fusion"]) for f in findings if f.metadata.get("fusion")]
    incidents = runtime.fusion.correlate(results) if runtime.fusion else []
    return {
        "findings": payload,
        "incidents": [
            {
                "id": i.incident_id,
                "kind": i.kind,
                "resource": i.resource_id,
                "severity": i.severity,
                "summary": i.summary,
                "count": len(i.finding_ids),
            }
            for i in incidents
        ],
        "summary": {
            "total": len(payload),
            "auto": sum(1 for p in payload if p["decision"] == RiskDecision.AUTO_REMEDIATE.value),
            "held": sum(
                1 for p in payload if p["ruleOnlyDecision"] == "AUTO_REMEDIATE" and p["decision"] != "AUTO_REMEDIATE"
            ),
            "escalations": sum(1 for p in payload if p["escalate"]),
        },
    }


def run_remediate(raw_estate: Any, finding_ids: Any) -> dict[str, Any]:
    estate = validate_estate(raw_estate)
    if not isinstance(finding_ids, list) or not all(isinstance(x, str) for x in finding_ids) or len(finding_ids) > 100:
        raise ValidationError("findingIds must be a list of strings")
    runtime = _build_runtime(estate)
    findings = _scan(runtime, estate)
    chosen = safe_remediation_order([f for f in findings if f.finding_id in set(finding_ids)])
    outcomes = []
    for f in chosen:
        res = runtime.remediation_workflow.run(f)
        outcomes.append(
            {
                "findingId": f.finding_id,
                "resource": f.resource_id,
                "cloud": _cloud_of(f),
                "rule": f.rule_id,
                "action": res.action_result.action_id,
                "verified": res.verification.verified,
                "verification": res.verification.outcome.value,
                "message": res.verification.message,
                "before": posture_lines(res.verification.before_state or f.before_state),
                "after": posture_lines(res.verification.after_state),
            }
        )
    audit = [
        {"action": r.action, "result": r.result, "resource": r.resource_id, "rule": r.rule_id}
        for r in runtime.audit.list_records()
        if r.action in {"REMEDIATION_EXECUTED", "VERIFICATION_COMPLETED"}
    ]
    return {"outcomes": outcomes, "estate": {**estate, "resources": _inspect_controls(runtime, estate)}, "audit": audit}


def make_policy(buckets: Any, audit_bucket: Any = None) -> dict[str, Any]:
    if not isinstance(buckets, list) or not 1 <= len(buckets) <= 20:
        raise ValidationError("buckets must be a list of 1-20 names")
    for b in buckets + ([audit_bucket] if audit_bucket else []):
        if not isinstance(b, str) or not _NAME.match(b):
            raise ValidationError(f"invalid bucket name: {str(b)[:40]!r}")
    policies = generate_policies(buckets, audit_bucket=audit_bucket or None)
    return {
        role: {
            "policy": p.document,
            "rationale": p.rationale,
            "reviewChecklist": p.review_checklist,
            "problems": validate_least_privilege(p),
        }
        for role, p in policies.items()
    }


# --- real AWS accounts ---------------------------------------------------------------------------------------------
MAX_BUCKETS = 200
TAG_KEY = "aspare-autofix"


def _real_runtime(body: dict[str, Any]) -> Runtime:
    import boto3
    from botocore.config import Config

    creds = body.get("credentials") or {}
    for key in ("accessKeyId", "secretAccessKey", "sessionToken"):
        if not isinstance(creds.get(key), str) or not creds[key]:
            raise ValidationError("credentials are incomplete")
    region = str(body.get("region") or "us-east-1")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", region):
        raise ValidationError("invalid region")
    allowed = body.get("allowedBuckets") or []
    if not isinstance(allowed, list) or not all(isinstance(b, str) and _NAME.match(b) for b in allowed):
        raise ValidationError("allowedBuckets must be a list of bucket names")
    session = boto3.Session(
        aws_access_key_id=creds["accessKeyId"],
        aws_secret_access_key=creds["secretAccessKey"],
        aws_session_token=creds["sessionToken"],
        region_name=region,
    )
    s3 = session.client("s3", config=Config(retries={"max_attempts": 6, "mode": "adaptive"}, max_pool_connections=24))
    settings = replace(
        Settings.from_env(),
        region=region,
        allowed_buckets=frozenset(allowed),
        require_demo_tag=True,
        demo_tag_key=TAG_KEY,
        demo_tag_value="true",
        dry_run=False,
        audit_backend="memory",
        event_bus_name=None,
        alert_topic_arn=None,
        fusion_enabled=True,
    )
    return build_runtime(settings, client=s3)


def scan_account(body: dict[str, Any]) -> dict[str, Any]:
    """Read-only scan of every bucket (up to MAX_BUCKETS) in the account the credentials belong to."""
    runtime = _real_runtime(body)
    names = sorted(runtime.inspector.list_resource_ids())
    truncated = len(names) > MAX_BUCKETS
    names = names[:MAX_BUCKETS]
    snapshots = runtime.inspector.prefetch(names, workers=12)
    findings: list[Finding] = []
    for name in names:
        findings += runtime.detection_workflow.run_raw(
            {"source": "aspare.scheduler", "detail": {"buckets": [name], "region": runtime.settings.region}}
        ).findings
    published = getattr(runtime.publisher, "published", None)
    if published is not None:
        published.clear()
    by_bucket: dict[str, int] = {}
    for f in findings:
        by_bucket[f.resource_id] = by_bucket.get(f.resource_id, 0) + 1
    inventory = [
        {
            "name": n,
            "tags": snapshots[n].tags if n in snapshots else {},
            "readable": n in snapshots,
            "findings": by_bucket.get(n, 0),
            "autofixOptIn": bool(snapshots[n].tags.get(TAG_KEY) == "true") if n in snapshots else False,
        }
        for n in names
    ]
    payload = sorted((_finding_payload(runtime, f) for f in findings), key=lambda p: -(p["priority"] or 0))
    for p in payload:
        res = snapshots.get(p["resource"])
        p["autofixAllowed"] = bool(res and runtime.settings.is_bucket_allowed(p["resource"], res.tags))
    results = [FusionResult.from_dict(f.metadata["fusion"]) for f in findings if f.metadata.get("fusion")]
    incidents = runtime.fusion.correlate(results) if runtime.fusion else []
    return {
        "findings": payload,
        "inventory": inventory,
        "incidents": [
            {
                "id": i.incident_id,
                "kind": i.kind,
                "resource": i.resource_id,
                "severity": i.severity,
                "summary": i.summary,
                "count": len(i.finding_ids),
            }
            for i in incidents
        ],
        "summary": {
            "buckets": len(names),
            "unreadable": sum(1 for i in inventory if not i["readable"]),
            "truncated": truncated,
            "total": len(payload),
            "auto": sum(1 for p in payload if p["decision"] == RiskDecision.AUTO_REMEDIATE.value),
            "held": sum(
                1 for p in payload if p["ruleOnlyDecision"] == "AUTO_REMEDIATE" and p["decision"] != "AUTO_REMEDIATE"
            ),
            "escalations": sum(1 for p in payload if p["escalate"]),
        },
    }


def remediate_account(body: dict[str, Any]) -> dict[str, Any]:
    """Apply the chosen findings (the safety gate still refuses anything outside allow-list + opt-in tag)."""
    ids = body.get("findingIds")
    buckets = body.get("buckets")
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids) or len(ids) > 100:
        raise ValidationError("findingIds must be a list of strings")
    valid = (
        isinstance(buckets, list)
        and len(buckets) <= 100
        and all(isinstance(b, str) and _NAME.match(b) for b in buckets)
    )
    if not valid:
        raise ValidationError("buckets must be a list of bucket names")
    runtime = _real_runtime(body)
    runtime.inspector.prefetch(sorted(set(buckets)), workers=8)
    findings: list[Finding] = []
    for name in sorted(set(buckets)):
        findings += runtime.detection_workflow.run_raw(
            {"source": "aspare.scheduler", "detail": {"buckets": [name], "region": runtime.settings.region}}
        ).findings
    published = getattr(runtime.publisher, "published", None)
    if published is not None:
        published.clear()
    chosen = safe_remediation_order([f for f in findings if f.finding_id in set(ids)])
    outcomes = []
    for f in chosen:
        res = runtime.remediation_workflow.run(f)
        outcomes.append(
            {
                "findingId": f.finding_id,
                "resource": f.resource_id,
                "rule": f.rule_id,
                "action": res.action_result.action_id,
                "status": res.action_result.status.value,
                "verified": res.verification.verified,
                "verification": res.verification.outcome.value,
                "message": res.verification.message,
                "before": posture_lines(res.verification.before_state or f.before_state),
                "after": posture_lines(res.verification.after_state),
            }
        )
    return {"outcomes": outcomes}
