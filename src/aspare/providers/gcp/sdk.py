"""Real GCS implementation of ``GcsApi`` over ``google-cloud-storage`` (install ``aspare[gcp]``).

Not exercised in CI (needs a project); the mapping logic above it is covered with a fake API. Required roles:
``roles/storage.legacyBucketReader`` / ``storage.buckets.get`` for detection, ``roles/storage.admin`` scoped to the
allowlisted buckets for remediation. Authenticate with ``gcloud auth application-default login``.
"""

from __future__ import annotations

from typing import Any

_PUBLIC = {"allUsers", "allAuthenticatedUsers"}


class SdkGcsApi:
    def __init__(self, project: str | None = None, client: Any | None = None) -> None:
        from google.cloud import storage

        self._client = client or storage.Client(project=project)

    def list_buckets(self) -> list[str]:
        return [b.name for b in self._client.list_buckets()]

    def get_bucket(self, name: str) -> dict[str, Any]:
        b = self._client.get_bucket(name)
        return {
            "location": b.location,
            "labels": dict(b.labels or {}),
            "uniform_bucket_level_access": b.iam_configuration.uniform_bucket_level_access_enabled,
            "public_access_prevention": b.iam_configuration.public_access_prevention,
            "versioning_enabled": b.versioning_enabled,
            "default_kms_key": b.default_kms_key_name,
        }

    def patch_bucket(self, name: str, **changes: Any) -> None:
        b = self._client.get_bucket(name)
        if "public_access_prevention" in changes:
            b.iam_configuration.public_access_prevention = changes["public_access_prevention"]
        if "uniform_bucket_level_access" in changes:
            b.iam_configuration.uniform_bucket_level_access_enabled = changes["uniform_bucket_level_access"]
        if "versioning_enabled" in changes:
            b.versioning_enabled = changes["versioning_enabled"]
        b.patch()

    def get_iam_bindings(self, name: str) -> list[dict[str, Any]]:
        policy = self._client.bucket(name).get_iam_policy(requested_policy_version=3)
        return [{"role": b["role"], "members": sorted(b["members"])} for b in policy.bindings]

    def remove_public_iam_members(self, name: str) -> list[dict[str, Any]]:
        bucket = self._client.bucket(name)
        policy = bucket.get_iam_policy(requested_policy_version=3)
        removed: list[dict[str, Any]] = []
        for binding in policy.bindings:
            hits = sorted(set(binding["members"]) & _PUBLIC)
            if hits:
                removed.append({"role": binding["role"], "members": hits})
                binding["members"] = set(binding["members"]) - _PUBLIC
        policy.bindings = [b for b in policy.bindings if b["members"]]
        bucket.set_iam_policy(policy)
        return removed
