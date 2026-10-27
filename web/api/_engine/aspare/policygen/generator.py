"""Generate the smallest IAM policies ASPARe needs, from the actions it will actually run.

The action -> IAM mapping is data in this module, and ``tests/unit/test_policygen.py`` proves it complete: it records
every S3 API operation the inspector and each remediation action really perform and checks the generated policy
covers all of them. Generated policies are *proposals*: they carry a review checklist and are never applied
automatically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from aspare.core.models import Finding

# S3 operations whose IAM action name differs from the API operation name.
_OPERATION_ALIASES = {
    "HeadBucket": "s3:ListBucket",
    "GetBucketEncryption": "s3:GetEncryptionConfiguration",
    "PutBucketEncryption": "s3:PutEncryptionConfiguration",
    "DeleteBucketEncryption": "s3:PutEncryptionConfiguration",
    "ListBuckets": "s3:ListAllMyBuckets",
    "GetPublicAccessBlock": "s3:GetBucketPublicAccessBlock",
    "PutPublicAccessBlock": "s3:PutBucketPublicAccessBlock",
    "DeletePublicAccessBlock": "s3:PutBucketPublicAccessBlock",
}

# Read-only calls made by S3Inspector (also used for post-remediation verification and the safety gate).
INSPECTION_ACTIONS = (
    "s3:ListBucket",
    "s3:GetBucketLocation",
    "s3:GetBucketTagging",
    "s3:GetBucketAcl",
    "s3:GetBucketPolicy",
    "s3:GetBucketVersioning",
    "s3:GetEncryptionConfiguration",
    "s3:GetBucketPublicAccessBlock",
    "s3:GetBucketOwnershipControls",
)

# Write permissions per remediation action id (the reads they also need are in INSPECTION_ACTIONS).
ACTION_WRITE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "S3_BLOCK_PUBLIC_ACCESS": ("s3:PutBucketPublicAccessBlock",),
    "S3_ENABLE_DEFAULT_ENCRYPTION": ("s3:PutEncryptionConfiguration",),
    "S3_ENABLE_VERSIONING": ("s3:PutBucketVersioning",),
    "S3_ENFORCE_HTTPS": ("s3:PutBucketPolicy",),
    "S3_REMOVE_PUBLIC_ACL": ("s3:PutBucketAcl",),
}


def iam_action_for_operation(operation: str) -> str:
    """Map a botocore S3 operation name (e.g. ``PutBucketVersioning``) to its IAM action."""
    return _OPERATION_ALIASES.get(operation, f"s3:{operation}")


@dataclass
class GeneratedPolicy:
    role: str
    document: dict[str, Any]
    rationale: dict[str, str] = field(default_factory=dict)
    review_checklist: list[str] = field(default_factory=list)

    def actions(self) -> set[str]:
        out: set[str] = set()
        for statement in self.document["Statement"]:
            actions = statement["Action"]
            out.update([actions] if isinstance(actions, str) else actions)
        return out

    def to_json(self) -> str:
        return json.dumps(
            {
                "role": self.role,
                "policy": self.document,
                "rationale": self.rationale,
                "review_checklist": self.review_checklist,
            },
            indent=2,
        )


def required_actions(findings: list[Finding] | None = None, action_ids: list[str] | None = None) -> list[str]:
    """Remediation action ids ASPARe needs: from findings if given, else the explicit list, else all known."""
    if findings is not None:
        found = {f.remediation_action for f in findings if f.remediation_action in ACTION_WRITE_PERMISSIONS}
        return sorted(found)
    if action_ids is not None:
        unknown = set(action_ids) - set(ACTION_WRITE_PERMISSIONS)
        if unknown:
            raise ValueError(f"Unknown remediation action(s): {sorted(unknown)}")
        return sorted(set(action_ids))
    return sorted(ACTION_WRITE_PERMISSIONS)


def generate_policies(
    buckets: list[str],
    action_ids: list[str] | None = None,
    findings: list[Finding] | None = None,
    audit_bucket: str | None = None,
    alert_topic_arn: str | None = None,
    event_bus_arn: str | None = None,
    log_group_arns: dict[str, str] | None = None,
) -> dict[str, GeneratedPolicy]:
    """Return ``{"detection": ..., "remediation": ...}`` policies scoped to the given buckets."""
    if not buckets:
        raise ValueError("At least one bucket is required: ASPARe never gets account-wide write access")
    bucket_arns = [f"arn:aws:s3:::{b}" for b in sorted(set(buckets))]
    needed = required_actions(findings, action_ids)
    writes = sorted({perm for a in needed for perm in ACTION_WRITE_PERMISSIONS[a]})

    def base(role: str, extra_actions: list[str]) -> GeneratedPolicy:
        statements: list[dict[str, Any]] = [
            {
                "Sid": "InspectAllowlistedBuckets",
                "Effect": "Allow",
                "Action": list(INSPECTION_ACTIONS),
                "Resource": bucket_arns,
            },
        ]
        rationale = {
            "InspectAllowlistedBuckets": "Read the control settings the inspector reads, for allowlisted buckets only.",
        }
        if role == "detection":
            statements.append(
                {"Sid": "ListBucketNames", "Effect": "Allow", "Action": ["s3:ListAllMyBuckets"], "Resource": "*"}
            )
            rationale["ListBucketNames"] = "ListAllMyBuckets cannot be scoped to a resource; it only returns names."
        if extra_actions:
            statements.append(
                {"Sid": "ApplyReviewedFixes", "Effect": "Allow", "Action": extra_actions, "Resource": bucket_arns}
            )
            rationale["ApplyReviewedFixes"] = "Only the write APIs behind the remediation actions below: " + ", ".join(
                needed
            )
        if audit_bucket:
            statements.append(
                {
                    "Sid": "WriteAuditObjects",
                    "Effect": "Allow",
                    "Action": ["s3:PutObject"],
                    "Resource": f"arn:aws:s3:::{audit_bucket}/audit/*",
                }
            )
            rationale["WriteAuditObjects"] = "Append-only audit records under audit/ in the audit bucket."
        if role == "detection":
            if event_bus_arn:
                statements.append(
                    {
                        "Sid": "PublishFindings",
                        "Effect": "Allow",
                        "Action": ["events:PutEvents"],
                        "Resource": event_bus_arn,
                    }
                )
                rationale["PublishFindings"] = (
                    "Hand AUTO_REMEDIATE findings to the remediation Lambda via the finding bus."
                )
            if alert_topic_arn:
                statements.append(
                    {"Sid": "SendAlerts", "Effect": "Allow", "Action": ["sns:Publish"], "Resource": alert_topic_arn}
                )
                rationale["SendAlerts"] = "Notify humans about findings that are not auto-remediated."
        if log_group_arns and role in log_group_arns:
            statements.append(
                {
                    "Sid": "WriteLogs",
                    "Effect": "Allow",
                    "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                    "Resource": log_group_arns[role],
                }
            )
            rationale["WriteLogs"] = "Lambda logs to its own log group only."
        checklist = [
            "Confirm every bucket ARN is intended; ASPARe can modify exactly these buckets.",
            "Confirm each write action matches a remediation you accept ASPARe performing automatically.",
            "Attach the permissions boundary / SCP your organization requires before applying.",
        ]
        return GeneratedPolicy(
            role=role,
            document={"Version": "2012-10-17", "Statement": statements},
            rationale=rationale,
            review_checklist=checklist,
        )

    return {"detection": base("detection", []), "remediation": base("remediation", writes)}


def validate_least_privilege(policy: GeneratedPolicy) -> list[str]:
    """Return violations; an empty list means the policy meets ASPARe's least-privilege rules."""
    problems: list[str] = []
    for statement in policy.document["Statement"]:
        actions = [statement["Action"]] if isinstance(statement["Action"], str) else statement["Action"]
        resources = [statement["Resource"]] if isinstance(statement["Resource"], str) else statement["Resource"]
        for action in actions:
            if action == "*" or action.endswith(":*"):
                problems.append(f"{statement['Sid']}: wildcard action {action}")
        for resource in resources:
            if resource == "*" and actions != ["s3:ListAllMyBuckets"]:
                problems.append(f"{statement['Sid']}: wildcard resource for {actions}")
            if resource.endswith("*") and statement["Sid"] != "WriteAuditObjects" and resource != "*":
                problems.append(f"{statement['Sid']}: wildcard resource {resource}")
        if statement.get("Effect") != "Allow":
            problems.append(f"{statement['Sid']}: unexpected effect {statement.get('Effect')}")
    return problems
