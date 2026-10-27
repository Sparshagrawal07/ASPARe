"""POST /api/scan  {estate} -> findings, incidents, summary (real ASPARe engine, simulated estate)."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import make_handler  # noqa: E402
from _lib.service import default_estate, run_scan  # noqa: E402

handler = make_handler(lambda body: run_scan(body.get("estate") or default_estate()))
