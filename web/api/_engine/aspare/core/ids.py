"""Deterministic identifiers for findings, audits, and correlation."""

from __future__ import annotations

import hashlib
import uuid


def finding_id(resource_id: str, rule_id: str, event_id: str | None = None) -> str:
    material = f"{resource_id}|{rule_id}|{event_id or 'scan'}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"fnd-{digest[:16]}"


def record_id(prefix: str = "aud") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def correlation_id(seed: str | None = None) -> str:
    if seed:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return f"cor-{digest[:16]}"
    return f"cor-{uuid.uuid4().hex[:16]}"
