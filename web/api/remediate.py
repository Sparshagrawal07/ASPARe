"""POST /api/remediate  {estate, findingIds} -> verified outcomes, updated estate, audit trail."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import make_handler  # noqa: E402
from _lib.service import run_remediate  # noqa: E402

handler = make_handler(lambda body: run_remediate(body.get("estate"), body.get("findingIds")))
