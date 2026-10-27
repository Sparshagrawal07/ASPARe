"""POST /api/scan  {estate} -> findings, incidents, summary (real ASPARe engine, simulated estate)."""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import respond_post, send_json  # noqa: E402
from _lib.service import default_estate, run_scan  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        respond_post(self, lambda body: run_scan(body.get("estate") or default_estate()))

    def do_GET(self) -> None:  # noqa: N802
        send_json(self, 405, {"error": "use POST"})

    def log_message(self, *_: object) -> None:
        return
