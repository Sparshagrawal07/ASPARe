from aspare.detection.rules.s3 import default_s3_rules
from aspare.policy.registry import PolicyRegistry
from aspare.reporting.explainers import explainer_for, load_explainers, posture_lines


def test_every_s3_rule_has_an_explainer(repo_root):
    policies = PolicyRegistry.from_path(repo_root / "config" / "policies" / "s3.json")
    catalog = load_explainers()
    rules = default_s3_rules(policies)
    for rule in rules:
        assert rule.rule_id in catalog
        expl = explainer_for(rule.rule_id)
        assert expl["what"]
        assert expl["affects"]
        assert expl["remedy_does"]


def test_posture_lines_read_snake_case_snapshots():
    lines = posture_lines(
        {
            "public_access_block": {
                "block_public_acls": True,
                "ignore_public_acls": True,
                "block_public_policy": False,
                "restrict_public_buckets": False,
            },
            "encryption": {"algorithm": None},
            "versioning": {"status": None},
        }
    )
    assert "Public Access Block: 2/4 flags on" in lines
    assert "Default encryption: not configured" in lines
