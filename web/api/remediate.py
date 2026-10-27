"""POST /api/remediate  {estate, findingIds} -> verified outcomes, updated estate, audit trail."""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import respond_post, send_json  # noqa: E402
from _lib.service import run_remediate  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        respond_post(self, lambda body: run_remediate(body.get("estate"), body.get("findingIds")))

    def do_GET(self) -> None:  # noqa: N802
        send_json(self, 405, {"error": "use POST"})

    def log_message(self, *_: object) -> None:
        return
