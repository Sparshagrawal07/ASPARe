"""Tests for the website's engine service (web/api/_lib/service.py) and its sync with the real engine."""

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web" / "api"))

from _lib import service  # noqa: E402


def _tree_hash(base: Path, pattern: str) -> dict[str, str]:
    return {
        str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(base.rglob(pattern))
        if "__pycache__" not in p.parts
    }


def test_web_engine_copy_is_in_sync_with_the_source():
    """web/api/_engine is a copy for Vercel; run `node web/scripts/sync-engine.mjs` when this fails."""
    assert _tree_hash(ROOT / "src" / "aspare", "*.py") == _tree_hash(
        ROOT / "web" / "api" / "_engine" / "aspare", "*.py"
    )
    assert _tree_hash(ROOT / "config", "*.json") == _tree_hash(ROOT / "web" / "api" / "_engine" / "config", "*.json")


def test_default_estate_scan_shows_fusion_at_work():
    out = service.run_scan(service.default_estate())
    findings = out["findings"]
    assert {f["cloud"] for f in findings} == {"aws", "azure", "gcp"}
    marketing = next(
        f for f in findings if f["resource"] == "campus-marketing-site" and f["rule"] == "S3_PUBLIC_ACCESS"
    )
    assert marketing["ruleOnlyDecision"] == "AUTO_REMEDIATE" and marketing["decision"] == "ALERT_AND_LOG"
    ferpa = next(f for f in findings if f["resource"] == "ferpa-transcripts-prod" and f["rule"] == "S3_PUBLIC_ACCESS")
    assert ferpa["decision"] == "AUTO_REMEDIATE" and ferpa["anomaly"]["score"] > 0.7
    assert ferpa["analysis"]["recommendation"] and ferpa["standards"]
    assert any(i["kind"] == "actor-campaign" for i in out["incidents"])
    assert not any(f["resource"] == "payroll-archive" for f in findings)  # a clean bucket stays clean
    assert out["summary"]["held"] >= 1 and out["summary"]["escalations"] >= 0


def test_remediation_fixes_and_verifies_on_all_three_clouds():
    estate = service.default_estate()
    scan = service.run_scan(estate)
    ids = [f["id"] for f in scan["findings"] if f["decision"] == "AUTO_REMEDIATE"]
    result = service.run_remediate(estate, ids)
    assert result["outcomes"] and all(o["verified"] for o in result["outcomes"])
    assert {o["cloud"] for o in result["outcomes"]} == {"aws", "azure", "gcp"}
    controls = {r["name"]: r["controls"] for r in result["estate"]["resources"]}
    assert controls["ferpa-transcripts-prod"]["publicBlocked"] and controls["ferpa-transcripts-prod"]["https"]
    assert controls["campus-marketing-site"]["publicBlocked"] is False  # held for a human, untouched
    assert controls["studentportalprod"]["publicGrant"] is False
    again = service.run_scan(result["estate"])
    assert not any(f["decision"] == "AUTO_REMEDIATE" for f in again["findings"])


def test_human_approval_fixes_a_held_finding():
    estate = service.default_estate()
    held = next(
        f
        for f in service.run_scan(estate)["findings"]
        if f["resource"] == "campus-marketing-site" and f["rule"] == "S3_PUBLIC_ACCESS"
    )
    result = service.run_remediate(estate, [held["id"]])
    assert result["outcomes"][0]["verified"]
    assert next(r for r in result["estate"]["resources"] if r["name"] == "campus-marketing-site")["controls"][
        "publicBlocked"
    ]


def test_user_can_break_a_secure_bucket_and_asp_detects_it():
    estate = service.default_estate()
    payroll = next(r for r in estate["resources"] if r["name"] == "payroll-archive")
    payroll["controls"]["publicBlocked"] = False
    findings = service.run_scan(estate)["findings"]
    hit = next(f for f in findings if f["resource"] == "payroll-archive")
    assert hit["rule"] == "S3_PUBLIC_ACCESS" and hit["decision"] == "AUTO_REMEDIATE"


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"resources": []},
        {"resources": [{"cloud": "gcp2", "name": "abc"}]},
        {"resources": [{"cloud": "aws", "name": "Bad_Name!"}]},
        {"resources": [{"cloud": "aws", "name": "ok-name", "tags": {"a": 1}}]},
        {"resources": [{"cloud": "aws", "name": "ok-name", "controls": {"versioning": "yes"}}]},
        {
            "resources": [{"cloud": "aws", "name": "ok-name"}],
            "changes": [{"resource": "nope", "actor": "x", "eventName": "PutBucketAcl"}],
        },
        {
            "resources": [{"cloud": "aws", "name": "ok-name"}],
            "changes": [{"resource": "ok-name", "actor": "x", "eventName": "DropEverything"}],
        },
    ],
)
def test_inputs_are_validated(bad):
    with pytest.raises(service.ValidationError):
        service.run_scan(bad)


def test_policy_endpoint_generates_checked_policies_and_rejects_bad_names():
    out = service.make_policy(["my-bucket"], "my-audit")
    assert out["remediation"]["problems"] == [] and "s3:PutBucketPublicAccessBlock" in str(out["remediation"]["policy"])
    with pytest.raises(service.ValidationError):
        service.make_policy(["x; DROP"], None)
    with pytest.raises(service.ValidationError):
        service.make_policy([], None)


def test_web_engine_copy_is_self_contained_in_a_fresh_interpreter():
    """pytest has already imported `aspare` from src, which can hide path bugs. A clean process cannot cheat."""
    import json
    import subprocess

    code = (
        "import sys, json; sys.path.insert(0, 'web/api');"
        "from _lib import service;"
        "out = service.run_scan(service.default_estate());"
        "import aspare; print(json.dumps({'n': len(out['findings']), 'from': aspare.__file__}))"
    )
    run = subprocess.run(
        [sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}
    )
    assert run.returncode == 0, run.stderr[-800:]
    info = json.loads(run.stdout.strip().splitlines()[-1])
    assert info["n"] > 0 and "_engine" in info["from"]
