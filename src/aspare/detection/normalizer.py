"""Create normalized Finding objects from policy + resource evidence."""

from __future__ import annotations

from typing import Any

from aspare.core.enums import FindingStatus
from aspare.core.ids import correlation_id, finding_id
from aspare.core.models import Finding, PolicyDefinition, StorageEvent, StorageResource
from aspare.core.timeutil import utcnow


def normalize_finding(
    resource: StorageResource,
    policy: PolicyDefinition,
    evidence: dict[str, Any],
    event: StorageEvent | None = None,
) -> Finding:
    event_id = event.event_id if event else None
    corr = event.correlation_id if event else correlation_id(f"{resource.resource_id}:{policy.rule_id}")
    return Finding(
        finding_id=finding_id(resource.resource_id, policy.rule_id, event_id),
        resource_id=resource.resource_id,
        resource_type=resource.resource_type,
        provider=resource.provider,
        rule_id=policy.rule_id,
        policy_id=policy.policy_id,
        title=policy.title,
        description=policy.description,
        severity=policy.severity,
        detected_at=utcnow(),
        auto_remediable=policy.auto_remediable,
        remediation_action=policy.remediation_action,
        status=FindingStatus.DETECTED,
        correlation_id=corr,
        event_id=event_id,
        region=resource.region,
        metadata={"evidence": evidence, "standards": list(policy.standards)},
        before_state=resource.snapshot(),
    )
