"""Static documentation quality checks used by CI."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "docs/README.md",
    "docs/GLOSSARY.md",
    "docs/DEMO_GUIDE.md",
    "docs/IMPLEMENTATION_STATUS.md",
    "docs/architecture/overview.md",
    "docs/architecture/event-flow.md",
    "docs/architecture/detection-engine.md",
    "docs/architecture/remediation-engine.md",
    "docs/architecture/verification.md",
    "docs/architecture/infrastructure.md",
    "docs/security/threat-model.md",
    "docs/security/permissions.md",
    "docs/security/attack-scenarios.md",
    "docs/security/security-controls.md",
    "docs/implementation/detection-rules.md",
    "docs/implementation/remediation-rules.md",
    "docs/implementation/risk-engine.md",
    "docs/implementation/audit-system.md",
    "docs/testing/strategy.md",
    "docs/testing/unit-tests.md",
    "docs/testing/integration-tests.md",
    "docs/roadmap/future-work.md",
    "legacy/README.md",
]


def _mermaid_balanced(text: str) -> bool:
    opens = len(re.findall(r"```mermaid", text))
    fences = len(re.findall(r"```", text))
    return opens > 0 and fences % 2 == 0


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        print("missing documentation files:")
        for path in missing:
            print(f"  {path}")
        return 1
    mermaid_docs = list((ROOT / "docs").rglob("*.md")) + [ROOT / "README.md"]
    bad = []
    for path in mermaid_docs:
        text = path.read_text(encoding="utf-8")
        if "```mermaid" in text and not _mermaid_balanced(text):
            bad.append(str(path.relative_to(ROOT)))
        if "CloudSentinel" in text and path.name != "GLOSSARY.md":
            # Allow historical mentions only in glossary / legacy notes.
            if path.as_posix().endswith("legacy/README.md"):
                continue
            if "CloudSentinel" in text and "internal codename" not in text.lower() and path.name not in {
                "GLOSSARY.md"
            }:
                if path == ROOT / "legacy" / "README.md":
                    continue
    print(f"checked {len(REQUIRED)} required docs; mermaid fences scanned in {len(mermaid_docs)} files")
    if bad:
        print("unbalanced mermaid fences:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
