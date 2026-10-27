from dataclasses import replace

import boto3
import pytest
import yaml
from moto import mock_aws

from aspare.config.settings import Settings
from aspare.policygen import generate_policies, iam_action_for_operation, required_actions, validate_least_privilege
from aspare.policygen.generator import ACTION_WRITE_PERMISSIONS
from aspare.runtime import build_runtime

BUCKET = "policygen-bucket"


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)


def test_generated_policies_are_least_privilege():
    policies = generate_policies([BUCKET], audit_bucket="audit-b", alert_topic_arn="arn:aws:sns:r:1:t")
    for policy in policies.values():
        assert validate_least_privilege(policy) == []
        assert policy.review_checklist
    assert not any(a.startswith("s3:Put") for a in policies["detection"].actions() - {"s3:PutObject"})
    assert "s3:PutBucketPublicAccessBlock" in policies["remediation"].actions()


def test_policy_is_scoped_to_findings_not_everything():
    only = generate_policies([BUCKET], action_ids=["S3_ENABLE_VERSIONING"])["remediation"].actions()
    assert "s3:PutBucketVersioning" in only and "s3:PutBucketPolicy" not in only
    assert required_actions(action_ids=["S3_ENFORCE_HTTPS"]) == ["S3_ENFORCE_HTTPS"]
    with pytest.raises(ValueError):
        required_actions(action_ids=["NOPE"])
    with pytest.raises(ValueError):
        generate_policies([])


def test_wildcards_are_rejected():
    policy = generate_policies([BUCKET])["remediation"]
    policy.document["Statement"][0]["Action"].append("s3:*")
    assert any("wildcard action" in p for p in validate_least_privilege(policy))


@mock_aws
def test_policy_covers_every_api_call_the_code_really_makes(tmp_path):
    """Records the real S3 operations of the inspector and all remediation actions; the policy must allow them all."""
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET)
    client.put_bucket_tagging(Bucket=BUCKET, Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}]})
    seen: set[str] = set()
    client.meta.events.register(
        "before-call.s3.*", lambda model, **_: seen.add(iam_action_for_operation(model.name)), unique_id="rec"
    )
    settings = replace(
        Settings.from_env(),
        allowed_buckets=frozenset({BUCKET}),
        audit_backend="memory",
        event_bus_name=None,
        alert_topic_arn=None,
        fusion_enabled=False,
    )
    runtime = build_runtime(settings, client=client)
    out = runtime.pipeline.run_raw({"source": "aspare.direct", "detail": {"bucket": BUCKET, "region": "us-east-1"}})
    runtime.inspector.list_resource_ids()
    # run every action id once, even ones the pipeline did not need for this bucket
    from aspare.core.enums import FindingStatus
    from aspare.core.models import Finding

    template = out.detection.findings[0]
    for action_id in ACTION_WRITE_PERMISSIONS:
        probe = Finding(**{**template.__dict__, "remediation_action": action_id, "status": FindingStatus.CLASSIFIED})
        runtime.remediation_workflow.run(probe)
    allowed = set()
    for p in generate_policies([BUCKET]).values():
        allowed |= p.actions()
    # the audit bucket write is separate (JSONL here); everything else the code touched must be allowed
    missing = {a for a in seen if a not in allowed and a != "s3:PutObject"}
    assert not missing, f"generated policy would deny: {sorted(missing)}"


def test_deployed_template_matches_generated_s3_actions(repo_root):
    """Drift guard: the CloudFormation roles must grant exactly what the generator says is needed."""
    doc = yaml.load((repo_root / "infrastructure" / "aws" / "template.yaml").read_text(), Loader=_Loader)
    resources = doc["Resources"]

    def s3_actions(role):
        acts = set()
        for st in resources[role]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]:
            actions = st["Action"] if isinstance(st["Action"], list) else [st["Action"]]
            acts |= {a for a in actions if a.startswith("s3:") and a != "s3:PutObject"}
        return acts

    generated = generate_policies(["x"])
    assert s3_actions("DetectionRole") == generated["detection"].actions() - {"s3:PutObject"}
    assert s3_actions("RemediationRole") == generated["remediation"].actions() - {"s3:PutObject"}
