#!/usr/bin/env python3
"""Convenience wrapper: python scripts/demo.py --mode mocked"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aspare.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
