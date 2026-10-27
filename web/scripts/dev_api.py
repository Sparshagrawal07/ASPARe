"""Local stand-in for the Vercel Python functions: python scripts/dev_api.py (serves /api/* on :8000)."""

from __future__ import annotations

import os
import sys
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

# Share the Next.js dev secrets (ENGINE_SECRET) with this process.
_env = ROOT / ".env.local"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import engine  # noqa: E402
from _lib.http import make_handler  # noqa: E402
from _lib.service import default_estate, make_policy, run_remediate, run_scan  # noqa: E402

ROUTES = {
    "/api/estate": lambda b: default_estate(),
    "/api/scan": lambda b: run_scan(b.get("estate") or default_estate()),
    "/api/remediate": lambda b: run_remediate(b.get("estate"), b.get("findingIds")),
    "/api/policy": lambda b: make_policy(b.get("buckets"), b.get("auditBucket")),
}
HANDLERS = {path: make_handler(fn) for path, fn in ROUTES.items()}


class Router(make_handler(lambda b: {})):  # type: ignore[misc]
    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?")[0] == "/api/engine":
            return engine.handler.do_POST(self)  # type: ignore[arg-type]
        target = HANDLERS.get(self.path.split("?")[0])
        if not target:
            return self._send(404, {"error": "not found"})
        target.do_POST(self)  # type: ignore[arg-type]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"ASPARe dev API on http://127.0.0.1:{port}")
    HTTPServer(("127.0.0.1", port), Router).serve_forever()
