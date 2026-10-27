"""Locate the ``config/`` directory both in a source checkout and inside the Lambda package (``ASPARE_ROOT``)."""

from __future__ import annotations

import os
from pathlib import Path

_CHECKOUT_ROOT = Path(__file__).resolve().parents[3]


def config_dir() -> Path:
    return Path(os.environ.get("ASPARE_ROOT", str(_CHECKOUT_ROOT))) / "config"
