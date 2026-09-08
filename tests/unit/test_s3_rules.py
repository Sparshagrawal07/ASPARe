from tests.fixtures.builders import (
    acl_disabled_bucket,
    missing_https_bucket,
    public_bucket,
    secure_bucket,
    unencrypted_bucket,
    unsafe_acl_bucket,
    versioning_disabled_bucket,
)

from aspare.detection.rules.s3.acl import PublicAclRule
from aspare.detection.rules.s3.encryption import EncryptionDisabledRule
from aspare.detection.rules.s3.https import HttpsEnforcementRule
from aspare.detection.rules.s3.public_access import PublicAccessRule
from aspare.detection.rules.s3.versioning import VersioningDisabledRule


def test_public_access_detects_incomplete_block(policy_registry):
    finding = PublicAccessRule(policy_registry.by_rule("S3_PUBLIC_ACCESS")).detect(public_bucket())
    assert finding is not None
    assert finding.severity.value == "CRITICAL"
    assert finding.auto_remediable is True
    assert finding.remediation_action == "S3_BLOCK_PUBLIC_ACCESS"


def test_public_access_secure_bucket_is_clean(policy_registry):
    assert PublicAccessRule(policy_registry.by_rule("S3_PUBLIC_ACCESS")).detect(secure_bucket()) is None


def test_encryption_detects_missing_config(policy_registry):
    finding = EncryptionDisabledRule(policy_registry.by_rule("S3_ENCRYPTION_DISABLED")).detect(
        unencrypted_bucket()
    )
    assert finding is not None
    assert finding.severity.value == "HIGH"


def test_encryption_accepts_aes256(policy_registry):
    assert (
        EncryptionDisabledRule(policy_registry.by_rule("S3_ENCRYPTION_DISABLED")).detect(secure_bucket())
        is None
    )


def test_versioning_detects_disabled(policy_registry):
    finding = VersioningDisabledRule(policy_registry.by_rule("S3_VERSIONING_DISABLED")).detect(
        versioning_disabled_bucket()
    )
    assert finding is not None
    assert finding.severity.value == "MEDIUM"


def test_https_detects_missing_deny(policy_registry):
    finding = HttpsEnforcementRule(policy_registry.by_rule("S3_HTTPS_ENFORCEMENT_MISSING")).detect(
        missing_https_bucket()
    )
    assert finding is not None
    assert finding.severity.value == "HIGH"


def test_https_secure_policy_is_clean(policy_registry):
    assert (
        HttpsEnforcementRule(policy_registry.by_rule("S3_HTTPS_ENFORCEMENT_MISSING")).detect(secure_bucket())
        is None
    )


def test_acl_detects_all_users_grant(policy_registry):
    finding = PublicAclRule(policy_registry.by_rule("S3_PUBLIC_ACL_EXPOSURE")).detect(unsafe_acl_bucket())
    assert finding is not None
    assert finding.severity.value == "CRITICAL"


def test_acl_bucket_owner_enforced_is_clean(policy_registry):
    assert PublicAclRule(policy_registry.by_rule("S3_PUBLIC_ACL_EXPOSURE")).detect(acl_disabled_bucket()) is None
