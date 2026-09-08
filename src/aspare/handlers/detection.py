"""Thin Lambda/CLI handlers. Dependency construction lives in runtime.py."""

from __future__ import annotations

import json
from typing import Any

from aspare.audit.repository import AuditPersistenceError
from aspare.core.models import Finding
from aspare.logging import get_logger, log_event
from aspare.runtime import Runtime, build_runtime

_LOGGER = get_logger("aspare.handlers")
_RUNTIME: Runtime | None = None


def get_runtime() -> Runtime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = build_runtime()
    return _RUNTIME


def reset_runtime() -> None:
    global _RUNTIME
    _RUNTIME = None


def detection_handler(event: dict[str, Any], context: Any | None = None) -> dict[str, Any]:
    runtime = get_runtime()
    try:
        outcome = runtime.detection_workflow.run_raw(event)
    except AuditPersistenceError as exc:
        log_event(_LOGGER, "audit_persistence_failed", error=str(exc))
        raise
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "resources": [item.resource_id for item in outcome.resources],
                "findings": [item.to_dict() for item in outcome.findings],
                "classified": [
                    {"finding_id": item.finding.finding_id, "decision": item.decision.value}
                    for item in outcome.classified
                ],
                "errors": outcome.errors,
            }
        ),
    }


def remediation_handler(event: dict[str, Any], context: Any | None = None) -> dict[str, Any]:
    runtime = get_runtime()
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else event
    if isinstance(detail, str):
        detail = json.loads(detail)
    finding = Finding.from_dict(detail if "finding_id" in detail else event)
    try:
        outcome = runtime.remediation_workflow.run(finding)
    except AuditPersistenceError as exc:
        log_event(_LOGGER, "audit_persistence_failed", error=str(exc))
        raise
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "finding_id": outcome.finding.finding_id,
                "status": outcome.status.value,
                "action": outcome.action_result.to_dict(),
                "verification": outcome.verification.to_dict(),
            }
        ),
    }


# AWS Lambda entrypoints expected by the deployment template.
lambda_handler = detection_handler
