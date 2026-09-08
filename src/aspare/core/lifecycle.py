"""Finding lifecycle transitions for the deterministic pipeline."""

from aspare.core.enums import FindingStatus, RiskDecision
from aspare.core.models import Finding

_ALLOWED: dict[FindingStatus, set[FindingStatus]] = {
    FindingStatus.DETECTED: {FindingStatus.CLASSIFIED},
    FindingStatus.CLASSIFIED: {
        FindingStatus.PENDING_REMEDIATION,
        FindingStatus.ALERT_AND_LOG,
        FindingStatus.LOG_ONLY,
    },
    FindingStatus.PENDING_REMEDIATION: {FindingStatus.REMEDIATING},
    FindingStatus.REMEDIATING: {FindingStatus.VERIFYING, FindingStatus.REMEDIATION_FAILED},
    FindingStatus.VERIFYING: {FindingStatus.REMEDIATED, FindingStatus.REMEDIATION_FAILED},
    FindingStatus.ALERT_AND_LOG: set(),
    FindingStatus.LOG_ONLY: set(),
    FindingStatus.REMEDIATED: set(),
    FindingStatus.REMEDIATION_FAILED: set(),
}


class InvalidLifecycleTransition(ValueError):
    pass


def transition(finding: Finding, target: FindingStatus) -> Finding:
    allowed = _ALLOWED.get(finding.status, set())
    if target not in allowed:
        raise InvalidLifecycleTransition(f"{finding.status} cannot transition to {target}")
    finding.status = target
    return finding


def status_for_decision(decision: RiskDecision) -> FindingStatus:
    mapping = {
        RiskDecision.AUTO_REMEDIATE: FindingStatus.PENDING_REMEDIATION,
        RiskDecision.ALERT_AND_LOG: FindingStatus.ALERT_AND_LOG,
        RiskDecision.LOG_ONLY: FindingStatus.LOG_ONLY,
        RiskDecision.MANUAL_REVIEW: FindingStatus.ALERT_AND_LOG,
    }
    return mapping[decision]
