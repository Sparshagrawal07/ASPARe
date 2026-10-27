"""POST /api/estate -> the default demo estate."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _lib.http import make_handler  # noqa: E402
from _lib.service import default_estate  # noqa: E402

handler = make_handler(lambda body: default_estate())
