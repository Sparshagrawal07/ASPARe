"""POST /api/policy  {buckets, auditBucket?} -> least-privilege IAM policies."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import make_handler  # noqa: E402
from _lib.service import make_policy  # noqa: E402

handler = make_handler(lambda body: make_policy(body.get("buckets"), body.get("auditBucket")))
