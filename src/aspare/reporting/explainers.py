"""Operator-facing What / How / Remedy copy for each detection rule."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
DEFAULT_PATH = _REPO / "config" / "explainers.json"


@lru_cache(maxsize=1)
def load_explainers(path: str | None = None) -> dict[str, dict[str, Any]]:
    target = Path(path) if path else DEFAULT_PATH
    payload = json.loads(target.read_text())
    if not isinstance(payload, dict):
        raise ValueError("explainers.json must be an object keyed by rule_id")
    return payload


def explainer_for(rule_id: str) -> dict[str, Any]:
    catalog = load_explainers()
    found = catalog.get(rule_id)
    if found:
        return found
    return {
        "title": rule_id.replace("_", " ").title(),
        "what": "This control failed the policy knowledge base check.",
        "how": "The inspected snapshot did not match the expected evidence for this rule.",
        "affects": "The bucket is out of policy until the control is restored.",
        "blast_radius": "See the linked CIS / FSBP mapping on the finding.",
        "remedy_name": "Apply the mapped remediation action",
        "remedy_does": "ASPARe runs the action listed on the policy if risk allows auto-remediation.",
        "remedy_leaves": "Verification re-runs the same detector on a fresh snapshot.",
        "standards": [],
    }


def posture_lines(state: dict[str, Any] | None) -> list[str]:
    if not state:
        return []
    lines: list[str] = []
    pab = state.get("public_access_block") or {}
    if pab:
        values = [
            pab.get("block_public_acls"),
            pab.get("ignore_public_acls"),
            pab.get("block_public_policy"),
            pab.get("restrict_public_buckets"),
        ]
        if any(item is not None for item in values):
            on = sum(1 for item in values if item is True)
            lines.append(f"Public Access Block: {on}/4 flags on")
    enc = state.get("encryption") or {}
    if enc:
        algo = enc.get("algorithm")
        lines.append(f"Default encryption: {algo or 'not configured'}")
    ver = state.get("versioning") or {}
    if ver:
        lines.append(f"Versioning: {ver.get('status') or 'disabled'}")
    policy = state.get("policy") or {}
    if policy:
        present = bool(policy.get("present") or policy.get("document"))
        lines.append("Bucket policy: present" if present else "Bucket policy: none")
    acl = state.get("acl") or {}
    grants = acl.get("grants") or []
    if grants:
        public = [
            grant
            for grant in grants
            if "AllUsers" in str(grant.get("grantee_uri") or "")
            or "AuthenticatedUsers" in str(grant.get("grantee_uri") or "")
        ]
        lines.append(f"ACL grants: {len(grants)} ({len(public)} public)")
    return lines
