"""Transparent deterministic severity weights. Not an anomaly or ML model."""

from __future__ import annotations

from aspare.core.enums import Severity

DEFAULT_WEIGHTS = {
    Severity.CRITICAL: 100,
    Severity.HIGH: 75,
    Severity.MEDIUM: 50,
    Severity.LOW: 25,
}


def severity_weight(severity: Severity, weights: dict[Severity, int] | None = None) -> int:
    table = weights or DEFAULT_WEIGHTS
    return int(table.get(severity, 0))
