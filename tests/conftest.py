"""Shared pytest fixtures."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aspare.config.settings import Settings
from aspare.policy.registry import PolicyRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def policy_registry(repo_root: Path) -> PolicyRegistry:
    return PolicyRegistry.from_path(repo_root / "config" / "policies" / "s3.json")


@pytest.fixture
def settings(tmp_path: Path, repo_root: Path) -> Settings:
    base = Settings.from_env()
    return replace(
        base,
        allowed_buckets=frozenset({"demo-bucket"}),
        require_demo_tag=False,
        dry_run=False,
        audit_backend="memory",
        audit_path=tmp_path / "audit.jsonl",
        policy_path=repo_root / "config" / "policies" / "s3.json",
        risk_policy_path=repo_root / "config" / "risk-policy.json",
        event_bus_name=None,
    )
