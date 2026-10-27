#!/usr/bin/env python3
"""Run the rule-only vs fused benchmark and write docs/research/benchmark.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aspare.intelligence.benchmark import run  # noqa: E402


def main() -> int:
    result = run()
    ro, fu = result["rule_only"], result["fused"]
    lines = [
        "# Rule-only vs fused triage benchmark",
        "",
        f"Cases: **{result['cases']}** synthetic, hand-labelled (`data/benchmark/cases.json`).",
        "",
        "> **Read this honestly.** Labels were authored by the project, not by independent annotators, and encode the",
        "> intent of the context policy. The set checks that fusion handles situations a severity-only policy cannot",
        "> express (intended-public buckets, scratch data, uncertain evidence, credential-misuse bursts). It is a",
        "> regression benchmark, **not** evidence of real-world accuracy.",
        "",
        "| Metric | Rule-only | Fused |",
        "| --- | ---: | ---: |",
        f"| Decision accuracy vs label | {ro['decision_accuracy']} | {fu['decision_accuracy']} |",
        f"| Unsafe auto-remediations (auto-fixed what should not be) | {ro['unsafe_auto_remediations']} | {fu['unsafe_auto_remediations']} |",
        f"| Missed auto-remediations | {ro['missed_auto_remediations']} | {fu['missed_auto_remediations']} |",
        f"| Needless alerts (alert for ignorable finding) | {ro['needless_alerts']} | {fu['needless_alerts']} |",
        f"| Precision@{fu['k']} for urgent findings | {ro['precision_at_k_urgent']} | {fu['precision_at_k_urgent']} |",
        "",
        "## Per-case decisions",
        "",
        "| Case | Expected | Rule-only | Fused | Urgent |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in result["rows"]:
        lines.append(
            f"| {r['case_id']} | {r['expected']} | {r['rule_only']} | {r['fused']} | {'yes' if r['urgent'] else ''} |"
        )
    out = ROOT / "docs" / "research" / "benchmark.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
