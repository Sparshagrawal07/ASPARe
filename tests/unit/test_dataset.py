from aspare.core.enums import RiskDecision
from aspare.dataset import detect, load_events, load_inventory, remediate, start_lab, stop_lab


def test_dataset_detects_recorded_ferpa_buckets(tmp_path):
    inventory = load_inventory()
    events = load_events()
    names = {bucket["name"] for bucket in inventory["buckets"]}
    assert "ferpa-student-record-demo-for-cap" in names
    assert "ferpa-remediation-results-cap" in names
    assert len(names) >= 40
    assert len(events) >= 40

    lab = start_lab(str(tmp_path / "audit.jsonl"))
    try:
        findings = detect(lab)
        resources = {item.resource_id for item in findings}
        assert "ferpa-student-record-demo-for-cap" in resources
        assert len(findings) >= 40
        assert any(item.rule_id == "S3_PUBLIC_ACCESS" for item in findings)
        remediations = remediate(lab, findings)
        assert remediations
        assert all(
            item.decision is not RiskDecision.AUTO_REMEDIATE
            for item in findings
            if item.rule_id == "S3_VERSIONING_DISABLED"
        )
    finally:
        stop_lab(lab)
