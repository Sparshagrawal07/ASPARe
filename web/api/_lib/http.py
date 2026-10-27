"""Tiny JSON-over-HTTP helpers shared by the Vercel Python functions and the local dev server.

Vercel finds a Python function by looking for a literal ``class handler(BaseHTTPRequestHandler)`` in each file under
``api/``, so the files declare that class themselves and delegate the work to these helpers.
"""

from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from typing import Any

from _lib.service import ValidationError

MAX_BODY = 64 * 1024


def send_json(h: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", "no-store")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def respond_post(h: BaseHTTPRequestHandler, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    try:
        length = int(h.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return send_json(h, 413, {"error": "request too large"})
        data = json.loads(h.rfile.read(length) or b"{}")
        if not isinstance(data, dict):
            raise ValidationError("body must be a JSON object")
        send_json(h, 200, fn(data))
    except (ValidationError, json.JSONDecodeError, KeyError, ValueError) as exc:
        send_json(h, 400, {"error": str(exc)})
    except Exception:  # noqa: BLE001 - never leak internals from a public endpoint
        traceback.print_exc(file=sys.stderr)  # visible in Vercel function logs only
        send_json(h, 500, {"error": "internal error"})


def make_handler(fn: Callable[[dict[str, Any]], dict[str, Any]]) -> type[BaseHTTPRequestHandler]:
    """Used by the local dev server only."""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict[str, Any]) -> None:
            send_json(self, status, payload)

        def do_POST(self) -> None:  # noqa: N802
            respond_post(self, fn)

        def do_GET(self) -> None:  # noqa: N802
            send_json(self, 405, {"error": "use POST"})

        def log_message(self, *_: Any) -> None:
            return

    return Handler
