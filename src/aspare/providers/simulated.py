"""In-memory Azure and GCS API implementations: used by tests and the dashboard's no-account multi-cloud demo."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class FakeAzureApi:
    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, Any]] = {}
        self.containers: dict[str, list[dict[str, Any]]] = {}
        self.versioning: dict[str, bool] = {}

    def add(
        self,
        name: str,
        *,
        tags: dict[str, str],
        public: bool,
        https_only: bool,
        containers: Iterable[dict[str, Any]] = (),
    ) -> None:
        self.accounts[name] = {
            "location": "australiaeast",
            "tags": tags,
            "allow_blob_public_access": True if public else False,
            "https_only": https_only,
        }
        self.containers[name] = [dict(c) for c in containers]
        self.versioning[name] = False

    def list_accounts(self) -> list[str]:
        return list(self.accounts)

    def get_account(self, name: str) -> dict[str, Any]:
        if name not in self.accounts:
            raise KeyError(name)
        return dict(self.accounts[name])

    def update_account(self, name: str, **changes: Any) -> None:
        for key, value in changes.items():
            if value is not None:
                self.accounts[name][key] = value

    def get_versioning(self, name: str) -> bool:
        return self.versioning[name]

    def set_versioning(self, name: str, enabled: bool) -> None:
        self.versioning[name] = enabled

    def list_containers(self, name: str) -> list[dict[str, Any]]:
        return [dict(c) for c in self.containers[name]]

    def set_container_private(self, name: str, container: str) -> None:
        for c in self.containers[name]:
            if c["name"] == container:
                c["public_access"] = "none"


class FakeGcsApi:
    def __init__(self) -> None:
        self.buckets: dict[str, dict[str, Any]] = {}
        self.iam: dict[str, list[dict[str, Any]]] = {}

    def add(
        self,
        name: str,
        *,
        labels: dict[str, str],
        public_iam: bool,
        prevention: str = "inherited",
        ubla: bool = False,
    ) -> None:
        self.buckets[name] = {
            "location": "AUSTRALIA-SOUTHEAST1",
            "labels": labels,
            "uniform_bucket_level_access": ubla,
            "public_access_prevention": prevention,
            "versioning_enabled": False,
            "default_kms_key": None,
        }
        members = ["user:admin@example.com"] + (["allUsers"] if public_iam else [])
        self.iam[name] = [{"role": "roles/storage.objectViewer", "members": members}]

    def list_buckets(self) -> list[str]:
        return list(self.buckets)

    def get_bucket(self, name: str) -> dict[str, Any]:
        if name not in self.buckets:
            raise KeyError(name)
        return dict(self.buckets[name])

    def patch_bucket(self, name: str, **changes: Any) -> None:
        self.buckets[name].update(changes)

    def get_iam_bindings(self, name: str) -> list[dict[str, Any]]:
        return [dict(b) for b in self.iam[name]]

    def remove_public_iam_members(self, name: str) -> list[dict[str, Any]]:
        removed = []
        for binding in self.iam[name]:
            hits = [m for m in binding["members"] if m in {"allUsers", "allAuthenticatedUsers"}]
            if hits:
                removed.append({"role": binding["role"], "members": hits})
                binding["members"] = [m for m in binding["members"] if m not in hits]
        return removed
