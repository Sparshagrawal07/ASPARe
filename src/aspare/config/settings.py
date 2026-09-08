"""Environment-backed ASPARe settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _split_csv(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    region: str = "us-east-1"
    allowed_buckets: frozenset[str] = field(default_factory=frozenset)
    require_demo_tag: bool = True
    demo_tag_key: str = "ASPAReDemo"
    demo_tag_value: str = "true"
    dry_run: bool = False
    audit_backend: str = "jsonl"
    audit_path: Path = Path("var/audit/aspare.jsonl")
    audit_bucket: str | None = None
    audit_prefix: str = "audit/"
    accepted_encryption_algorithms: tuple[str, ...] = ("AES256", "aws:kms", "aws:kms:dsse")
    encryption_algorithm: str = "AES256"
    encryption_kms_key_id: str | None = None
    policy_path: Path = _REPO_ROOT / "config" / "policies" / "s3.json"
    risk_policy_path: Path = _REPO_ROOT / "config" / "risk-policy.json"
    event_bus_name: str | None = None
    scan_all_allowlisted: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        repo = Path(os.environ.get("ASPARE_ROOT", str(_REPO_ROOT)))
        backend = os.environ.get("ASPARE_AUDIT_BACKEND", "jsonl")
        return cls(
            region=os.environ.get("ASPARE_REGION", os.environ.get("AWS_REGION", "us-east-1")),
            allowed_buckets=_split_csv(os.environ.get("ASPARE_ALLOWED_BUCKETS")),
            require_demo_tag=_bool(os.environ.get("ASPARE_REQUIRE_DEMO_TAG"), True),
            demo_tag_key=os.environ.get("ASPARE_DEMO_TAG_KEY", "ASPAReDemo"),
            demo_tag_value=os.environ.get("ASPARE_DEMO_TAG_VALUE", "true"),
            dry_run=_bool(os.environ.get("ASPARE_DRY_RUN"), False),
            audit_backend=backend,
            audit_path=Path(os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl")),
            audit_bucket=os.environ.get("ASPARE_AUDIT_BUCKET") or None,
            audit_prefix=os.environ.get("ASPARE_AUDIT_PREFIX", "audit/"),
            accepted_encryption_algorithms=tuple(
                item.strip()
                for item in os.environ.get(
                    "ASPARE_ACCEPTED_ENCRYPTION", "AES256,aws:kms,aws:kms:dsse"
                ).split(",")
                if item.strip()
            ),
            encryption_algorithm=os.environ.get("ASPARE_ENCRYPTION_ALGORITHM", "AES256"),
            encryption_kms_key_id=os.environ.get("ASPARE_KMS_KEY_ID") or None,
            policy_path=Path(
                os.environ.get("ASPARE_POLICY_PATH", str(repo / "config" / "policies" / "s3.json"))
            ),
            risk_policy_path=Path(
                os.environ.get("ASPARE_RISK_POLICY_PATH", str(repo / "config" / "risk-policy.json"))
            ),
            event_bus_name=os.environ.get("ASPARE_EVENT_BUS_NAME") or None,
            scan_all_allowlisted=_bool(os.environ.get("ASPARE_SCAN_ALL_ALLOWLISTED"), True),
        )

    def is_bucket_allowed(self, bucket: str, tags: dict[str, str] | None = None) -> bool:
        if self.allowed_buckets and bucket not in self.allowed_buckets:
            return False
        if not self.require_demo_tag:
            return True
        tags = tags or {}
        return tags.get(self.demo_tag_key) == self.demo_tag_value
