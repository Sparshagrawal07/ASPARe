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


class FakeS3Client:
    """Just enough of boto3's S3 client for S3Inspector/S3Remediator, with real ClientError semantics."""

    def __init__(self) -> None:
        self.state: dict[str, dict[str, Any]] = {}

    def add(
        self,
        name: str,
        *,
        tags: dict[str, str],
        pab: dict[str, bool] | None,
        encrypted: bool,
        versioning: bool,
        https_policy: bool,
        public_acl: bool,
        region: str = "us-east-1",
    ) -> None:
        self.state[name] = {
            "tags": tags,
            "pab": pab,
            "encryption": "AES256" if encrypted else None,
            "versioning": "Enabled" if versioning else None,
            "policy": None,
            "public_acl": public_acl,
            "region": region,
        }
        if https_policy:
            from aspare.s3.https_policy import secure_transport_statement

            self.state[name]["policy"] = {"Version": "2012-10-17", "Statement": [secure_transport_statement(name)]}

    # --- helpers ---------------------------------------------------------------------------------------------
    @staticmethod
    def _err(code: str, op: str) -> Exception:
        from botocore.exceptions import ClientError

        return ClientError({"Error": {"Code": code, "Message": code}}, op)

    def _b(self, bucket: str, op: str) -> dict[str, Any]:
        if bucket not in self.state:
            raise self._err("NoSuchBucket", op)
        return self.state[bucket]

    # --- reads -----------------------------------------------------------------------------------------------
    def list_buckets(self) -> dict[str, Any]:
        return {"Buckets": [{"Name": n} for n in self.state]}

    def head_bucket(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        self._b(Bucket, "HeadBucket")
        return {}

    def get_bucket_location(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        region = self._b(Bucket, "GetBucketLocation")["region"]
        return {"LocationConstraint": None if region == "us-east-1" else region}

    def get_public_access_block(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        pab = self._b(Bucket, "GetPublicAccessBlock")["pab"]
        if pab is None:
            raise self._err("NoSuchPublicAccessBlockConfiguration", "GetPublicAccessBlock")
        return {"PublicAccessBlockConfiguration": dict(pab)}

    def get_bucket_encryption(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        algo = self._b(Bucket, "GetBucketEncryption")["encryption"]
        if not algo:
            raise self._err("ServerSideEncryptionConfigurationNotFoundError", "GetBucketEncryption")
        rule = {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": algo}}
        return {"ServerSideEncryptionConfiguration": {"Rules": [rule]}}

    def get_bucket_versioning(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        status = self._b(Bucket, "GetBucketVersioning")["versioning"]
        return {"Status": status} if status else {}

    def get_bucket_policy(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        import json

        policy = self._b(Bucket, "GetBucketPolicy")["policy"]
        if policy is None:
            raise self._err("NoSuchBucketPolicy", "GetBucketPolicy")
        return {"Policy": json.dumps(policy)}

    def get_bucket_acl(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        from aspare.s3.https_policy import PUBLIC_ACL_URIS

        b = self._b(Bucket, "GetBucketAcl")
        grants = [{"Grantee": {"Type": "CanonicalUser", "ID": "owner"}, "Permission": "FULL_CONTROL"}]
        if b["public_acl"]:
            grants.append({"Grantee": {"Type": "Group", "URI": sorted(PUBLIC_ACL_URIS)[0]}, "Permission": "READ"})
        return {"Owner": {"ID": "owner"}, "Grants": grants}

    def get_bucket_ownership_controls(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        self._b(Bucket, "GetBucketOwnershipControls")
        raise self._err("OwnershipControlsNotFoundError", "GetBucketOwnershipControls")

    def get_bucket_tagging(self, Bucket: str) -> dict[str, Any]:  # noqa: N803
        tags = self._b(Bucket, "GetBucketTagging")["tags"]
        return {"TagSet": [{"Key": k, "Value": v} for k, v in tags.items()]}

    # --- writes ----------------------------------------------------------------------------------------------
    def put_public_access_block(self, Bucket: str, PublicAccessBlockConfiguration: dict[str, bool]) -> None:  # noqa: N803
        self._b(Bucket, "PutPublicAccessBlock")["pab"] = dict(PublicAccessBlockConfiguration)

    def put_bucket_encryption(self, Bucket: str, ServerSideEncryptionConfiguration: dict[str, Any]) -> None:  # noqa: N803
        rule = ServerSideEncryptionConfiguration["Rules"][0]["ApplyServerSideEncryptionByDefault"]
        self._b(Bucket, "PutBucketEncryption")["encryption"] = rule["SSEAlgorithm"]

    def put_bucket_versioning(self, Bucket: str, VersioningConfiguration: dict[str, str]) -> None:  # noqa: N803
        self._b(Bucket, "PutBucketVersioning")["versioning"] = VersioningConfiguration["Status"]

    def put_bucket_policy(self, Bucket: str, Policy: str) -> None:  # noqa: N803
        import json

        self._b(Bucket, "PutBucketPolicy")["policy"] = json.loads(Policy)

    def put_bucket_acl(self, Bucket: str, AccessControlPolicy: dict[str, Any]) -> None:  # noqa: N803
        from aspare.s3.https_policy import PUBLIC_ACL_URIS

        grants = AccessControlPolicy.get("Grants") or []
        self._b(Bucket, "PutBucketAcl")["public_acl"] = any(
            (g.get("Grantee") or {}).get("URI") in PUBLIC_ACL_URIS for g in grants
        )
