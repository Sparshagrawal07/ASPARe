from aspare.core.enums import RiskDecision, Severity
from aspare.core.models import Finding, FindingStatus, Provider, ResourceType
from aspare.core.timeutil import utcnow
from aspare.risk.evaluator import RiskEvaluator, RiskPolicy
from aspare.risk.scoring import severity_weight


def _finding(severity: Severity, auto: bool = True) -> Finding:
    return Finding(
        finding_id="fnd-1",
        resource_id="demo-bucket",
        resource_type=ResourceType.S3_BUCKET,
        provider=Provider.AWS,
        rule_id="S3_PUBLIC_ACCESS",
        policy_id="POL-S3-PUBLIC-ACCESS",
        title="t",
        description="d",
        severity=severity,
        detected_at=utcnow(),
        auto_remediable=auto,
        remediation_action="S3_BLOCK_PUBLIC_ACCESS",
        status=FindingStatus.DETECTED,
        correlation_id="cor-1",
    )


def test_critical_auto_fixable_is_auto_remediate():
    assert RiskEvaluator().evaluate(_finding(Severity.CRITICAL)) is RiskDecision.AUTO_REMEDIATE


def test_high_auto_fixable_is_auto_remediate():
    assert RiskEvaluator().evaluate(_finding(Severity.HIGH)) is RiskDecision.AUTO_REMEDIATE


def test_medium_is_alert_and_log():
    assert RiskEvaluator().evaluate(_finding(Severity.MEDIUM)) is RiskDecision.ALERT_AND_LOG


def test_low_is_log_only():
    assert RiskEvaluator().evaluate(_finding(Severity.LOW)) is RiskDecision.LOG_ONLY


def test_not_auto_remediable_goes_to_manual_review():
    assert RiskEvaluator().evaluate(_finding(Severity.CRITICAL, auto=False)) is RiskDecision.MANUAL_REVIEW


def test_severity_weights_are_deterministic():
    assert severity_weight(Severity.CRITICAL) == 100
    assert severity_weight(Severity.LOW) == 25


def test_policy_can_change_without_rewriting_rules():
    policy = RiskPolicy.default()
    custom = RiskPolicy(
        auto_remediate_severities=frozenset({Severity.CRITICAL}),
        alert_severities=frozenset({Severity.HIGH, Severity.MEDIUM}),
        log_only_severities=frozenset({Severity.LOW}),
        require_auto_remediable_for_auto=True,
        manual_review_when_not_auto_remediable=True,
        weights=policy.weights,
    )
    assert RiskEvaluator(custom).evaluate(_finding(Severity.HIGH)) is RiskDecision.ALERT_AND_LOG
