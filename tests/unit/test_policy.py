from aspare.policy.registry import PolicyRegistry, PolicyRegistryError
from aspare.s3.https_policy import HTTPS_SID, secure_transport_statement, statements_of


def test_policy_registry_loads_five_s3_controls(policy_registry: PolicyRegistry):
    assert len(policy_registry.all_enabled()) == 5
    assert policy_registry.by_rule("S3_PUBLIC_ACCESS").severity.value == "CRITICAL"
    assert policy_registry.action_for_rule("S3_HTTPS_ENFORCEMENT_MISSING") == "S3_ENFORCE_HTTPS"


def test_policy_registry_rejects_unknown_rule(policy_registry: PolicyRegistry):
    try:
        policy_registry.by_rule("S3_DOES_NOT_EXIST")
        raise AssertionError("expected error")
    except PolicyRegistryError:
        pass


def test_https_merge_preserves_existing_statements():
    existing = {
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "KeepMe", "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "*"}
        ],
    }
    statement = secure_transport_statement("demo-bucket")
    merged = existing["Statement"] + [statement]
    sids = [item.get("Sid") for item in statements_of({"Statement": merged})]
    assert "KeepMe" in sids
    assert HTTPS_SID in sids
