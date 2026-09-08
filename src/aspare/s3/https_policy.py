"""Deterministic S3 HTTPS policy helpers shared by detection and remediation."""

from __future__ import annotations

from typing import Any

HTTPS_SID = "ASPAReDenyInsecureTransport"
PUBLIC_ACL_URIS = {
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
}


def statements_of(document: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not document:
        return []
    statements = document.get("Statement") or []
    if isinstance(statements, dict):
        return [statements]
    return list(statements)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _condition_denies_insecure_transport(statement: dict[str, Any]) -> bool:
    condition = statement.get("Condition") or {}
    bool_cond = condition.get("Bool") or condition.get("bool") or {}
    values = _as_list(bool_cond.get("aws:SecureTransport") or bool_cond.get("aws:securetransport"))
    return any(item.lower() == "false" for item in values)


def _resources_cover_bucket(statement: dict[str, Any], bucket: str) -> bool:
    resources = _as_list(statement.get("Resource"))
    if not resources or "*" in resources:
        return True
    bucket_arn = f"arn:aws:s3:::{bucket}"
    object_arn = f"{bucket_arn}/*"
    has_bucket = any(item in {bucket_arn, "*"} or item.endswith(f":{bucket}") for item in resources)
    has_objects = any(item in {object_arn, "*"} or item.endswith(f":{bucket}/*") for item in resources)
    return has_bucket and has_objects


def has_secure_transport_deny(document: dict[str, Any] | None, bucket: str) -> bool:
    for statement in statements_of(document):
        if str(statement.get("Effect", "")).lower() != "deny":
            continue
        if not _condition_denies_insecure_transport(statement):
            continue
        if _resources_cover_bucket(statement, bucket):
            return True
    return False


def secure_transport_statement(bucket: str) -> dict[str, Any]:
    return {
        "Sid": HTTPS_SID,
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
        "Condition": {"Bool": {"aws:SecureTransport": "false"}},
    }
