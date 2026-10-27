"""POST /api/engine: signed internal endpoint used by the ASPARe backend to scan or fix a connected account.

The body carries short-lived credentials produced by the backend (STS AssumeRole), so this function never holds
long-lived secrets. Requests must be signed with HMAC-SHA256 over `timestamp.body` using ENGINE_SECRET.
"""

import hashlib
import hmac
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

from _lib.service import ValidationError, remediate_account, scan_account  # noqa: E402

MAX_BODY = 512 * 1024
SKEW_SECONDS = 300


def verify(secret: str, timestamp: str, signature: str, body: bytes) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > SKEW_SECONDS:
        return False
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def dispatch(body: dict) -> dict:
    action = body.get("action")
    if action == "scan":
        return scan_account(body)
    if action == "remediate":
        return remediate_account(body)
    raise ValidationError("unknown action")


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        secret = os.environ.get("ENGINE_SECRET", "")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "request too large"})
            raw = self.rfile.read(length)
            ts = self.headers.get("x-aspare-timestamp", "")
            sig = self.headers.get("x-aspare-signature", "")
            if not secret or not verify(secret, ts, sig, raw):
                return self._send(401, {"error": "unauthorized"})
            self._send(200, dispatch(json.loads(raw or b"{}")))
        except (ValidationError, json.JSONDecodeError, KeyError, ValueError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception:  # noqa: BLE001 - never leak internals
            traceback.print_exc(file=sys.stderr)
            self._send(500, {"error": "internal error"})

    def do_GET(self) -> None:  # noqa: N802
        self._send(405, {"error": "use POST"})

    def log_message(self, *_: object) -> None:
        return
