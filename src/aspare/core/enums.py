"""Enumerations used throughout the ASPARe deterministic baseline."""

from enum import StrEnum


class Provider(StrEnum):
    """Cloud provider identity. Only AWS is implemented in this milestone."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ResourceType(StrEnum):
    """Storage resource kinds. Azure/GCP values exist as future extension points."""

    S3_BUCKET = "s3_bucket"
    AZURE_BLOB_CONTAINER = "azure_blob_container"
    GCS_BUCKET = "gcs_bucket"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskDecision(StrEnum):
    AUTO_REMEDIATE = "AUTO_REMEDIATE"
    ALERT_AND_LOG = "ALERT_AND_LOG"
    LOG_ONLY = "LOG_ONLY"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class FindingStatus(StrEnum):
    DETECTED = "DETECTED"
    CLASSIFIED = "CLASSIFIED"
    PENDING_REMEDIATION = "PENDING_REMEDIATION"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    REMEDIATED = "REMEDIATED"
    REMEDIATION_FAILED = "REMEDIATION_FAILED"
    ALERT_AND_LOG = "ALERT_AND_LOG"
    LOG_ONLY = "LOG_ONLY"


class VerificationOutcome(StrEnum):
    VERIFIED = "VERIFIED"
    ACTION_FAILED = "ACTION_FAILED"
    REREAD_FAILED = "REREAD_FAILED"
    FINDING_PERSISTED = "FINDING_PERSISTED"
    UNSUPPORTED = "UNSUPPORTED"


class ActionResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    UNSUPPORTED = "UNSUPPORTED"
    DRY_RUN = "DRY_RUN"
    DENIED = "DENIED"


class EventType(StrEnum):
    CLOUDTRAIL_API_CALL = "cloudtrail_api_call"
    SCHEDULED_SCAN = "scheduled_scan"
    DIRECT_SCAN = "direct_scan"
    DEMO = "demo"


class AuditAction(StrEnum):
    SCAN_COMPLETED = "SCAN_COMPLETED"
    FINDING_DETECTED = "FINDING_DETECTED"
    RISK_EVALUATED = "RISK_EVALUATED"
    REMEDIATION_STARTED = "REMEDIATION_STARTED"
    REMEDIATION_EXECUTED = "REMEDIATION_EXECUTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    AUDIT_FALLBACK = "AUDIT_FALLBACK"
