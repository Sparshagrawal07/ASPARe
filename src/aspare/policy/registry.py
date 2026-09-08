"""Deterministic Policy Knowledge Base."""

from __future__ import annotations

import json
from pathlib import Path

from aspare.core.enums import ResourceType, Severity
from aspare.core.models import PolicyDefinition


class PolicyRegistryError(ValueError):
    pass


class PolicyRegistry:
    def __init__(self, policies: list[PolicyDefinition]) -> None:
        self._by_id = {policy.policy_id: policy for policy in policies}
        self._by_rule = {policy.rule_id: policy for policy in policies}
        self._validate()

    @classmethod
    def from_path(cls, path: str | Path) -> PolicyRegistry:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        policies = [cls._from_record(record) for record in payload.get("policies", [])]
        return cls(policies)

    def get(self, policy_id: str) -> PolicyDefinition:
        try:
            return self._by_id[policy_id]
        except KeyError as exc:
            raise PolicyRegistryError(f"Unknown policy_id {policy_id}") from exc

    def by_rule(self, rule_id: str) -> PolicyDefinition:
        try:
            return self._by_rule[rule_id]
        except KeyError as exc:
            raise PolicyRegistryError(f"Unknown rule_id {rule_id}") from exc

    def all_enabled(self) -> list[PolicyDefinition]:
        return [policy for policy in self._by_id.values() if policy.enabled]

    def all(self) -> list[PolicyDefinition]:
        return list(self._by_id.values())

    def action_for_rule(self, rule_id: str) -> str:
        return self.by_rule(rule_id).remediation_action

    def _validate(self) -> None:
        if not self._by_id:
            raise PolicyRegistryError("Policy Knowledge Base is empty")
        required = {
            "S3_PUBLIC_ACCESS",
            "S3_ENCRYPTION_DISABLED",
            "S3_VERSIONING_DISABLED",
            "S3_HTTPS_ENFORCEMENT_MISSING",
            "S3_PUBLIC_ACL_EXPOSURE",
        }
        missing = required - set(self._by_rule)
        if missing:
            raise PolicyRegistryError(f"Missing required S3 policies: {sorted(missing)}")
        if len(self._by_id) != len(self._by_rule):
            raise PolicyRegistryError("policy_id and rule_id must be unique and 1:1")

    @staticmethod
    def _from_record(record: dict) -> PolicyDefinition:
        return PolicyDefinition(
            policy_id=record["policy_id"],
            title=record["title"],
            description=record["description"],
            control_objective=record["control_objective"],
            resource_type=ResourceType(record["resource_type"]),
            rule_id=record["rule_id"],
            expected_evidence=tuple(record.get("expected_evidence") or ()),
            severity=Severity(record["severity"]),
            remediation_action=record["remediation_action"],
            auto_remediable=bool(record["auto_remediable"]),
            verification_rule=record["verification_rule"],
            standards=tuple(record.get("standards") or ()),
            enabled=bool(record.get("enabled", True)),
        )
