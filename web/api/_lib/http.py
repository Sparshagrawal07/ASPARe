"""Tiny JSON-over-HTTP helpers shared by the Vercel Python functions and the local dev server."""

from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from typing import Any

from _lib.service import ValidationError

MAX_BODY = 64 * 1024


def make_handler(fn: Callable[[dict[str, Any]], dict[str, Any]]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    return self._send(413, {"error": "request too large"})
                data = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(data, dict):
                    raise ValidationError("body must be a JSON object")
                self._send(200, fn(data))
            except (ValidationError, json.JSONDecodeError, KeyError, ValueError) as exc:
                self._send(400, {"error": str(exc)})
            except Exception:  # noqa: BLE001 - never leak internals from a public endpoint
                traceback.print_exc(file=sys.stderr)  # visible in Vercel function logs only
                self._send(500, {"error": "internal error"})

        def do_GET(self) -> None:  # noqa: N802
            self._send(405, {"error": "use POST"})

        def log_message(self, *_: Any) -> None:
            return

    return Handler
