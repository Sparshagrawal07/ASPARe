"""Builders for StorageResource fixtures used by unit tests."""

from __future__ import annotations

from aspare.core.enums import Provider, ResourceType
from aspare.core.models import (
    AclGrant,
    AclState,
    BucketPolicyState,
    EncryptionState,
    OwnershipState,
    PublicAccessBlockState,
    StorageResource,
    VersioningState,
)
from aspare.core.timeutil import utcnow
from aspare.s3.https_policy import PUBLIC_ACL_URIS, secure_transport_statement

ALL_USERS = next(iter(sorted(PUBLIC_ACL_URIS)))


def _resource(**overrides: object) -> StorageResource:
    base = dict(
        provider=Provider.AWS,
        resource_type=ResourceType.S3_BUCKET,
        resource_id="demo-bucket",
        region="us-east-1",
        tags={"ASPAReDemo": "true"},
        public_access_block=PublicAccessBlockState(
            present=True,
            block_public_acls=True,
            ignore_public_acls=True,
            block_public_policy=True,
            restrict_public_buckets=True,
        ),
        encryption=EncryptionState(present=True, enabled=True, algorithm="AES256"),
        versioning=VersioningState(present=True, status="Enabled"),
        policy=BucketPolicyState(
            present=True,
            document={"Version": "2012-10-17", "Statement": [secure_transport_statement("demo-bucket")]},
        ),
        acl=AclState(
            present=True,
            owner_id="owner",
            grants=(AclGrant("CanonicalUser", None, "owner", "FULL_CONTROL"),),
        ),
        ownership=OwnershipState(present=True, object_ownership="BucketOwnerPreferred"),
        inspected_at=utcnow(),
        inspection_errors=(),
    )
    base.update(overrides)
    return StorageResource(**base)  # type: ignore[arg-type]


def secure_bucket() -> StorageResource:
    return _resource()


def public_bucket() -> StorageResource:
    return _resource(
        public_access_block=PublicAccessBlockState(
            present=True,
            block_public_acls=False,
            ignore_public_acls=False,
            block_public_policy=False,
            restrict_public_buckets=False,
        )
    )


def unencrypted_bucket() -> StorageResource:
    return _resource(encryption=EncryptionState(present=False, enabled=False))


def versioning_disabled_bucket() -> StorageResource:
    return _resource(versioning=VersioningState(present=True, status=None))


def missing_https_bucket() -> StorageResource:
    return _resource(policy=BucketPolicyState(present=False, document=None))


def unsafe_acl_bucket() -> StorageResource:
    return _resource(
        acl=AclState(
            present=True,
            owner_id="owner",
            grants=(
                AclGrant("CanonicalUser", None, "owner", "FULL_CONTROL"),
                AclGrant("Group", ALL_USERS, None, "READ"),
            ),
        )
    )


def acl_disabled_bucket() -> StorageResource:
    return _resource(
        ownership=OwnershipState(present=True, object_ownership="BucketOwnerEnforced"),
        acl=AclState(
            present=True,
            owner_id="owner",
            grants=(AclGrant("Group", ALL_USERS, None, "READ"),),
        ),
    )
