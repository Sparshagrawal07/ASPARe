"""Human-impact configuration for the ASPARe dashboard.

The static human-impact map (api-contract.md §3) is defined alongside the
reporting aggregator so backend and dashboard share one source of truth.
This module re-exports it as the dashboard-owned config surface.
"""

from __future__ import annotations

from aspare.reporting.aggregator import HUMAN_IMPACT_MAP, SENSITIVE_CLASSES, HumanImpactEntry

__all__ = ["HUMAN_IMPACT_MAP", "HumanImpactEntry", "SENSITIVE_CLASSES"]

# Sensitive classes in dashboard display order (api-contract §3).
SENSITIVE_DISPLAY_ORDER = ("FERPA", "PHI", "FINANCIAL", "PII", "SECRETS")
