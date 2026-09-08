"""Structured JSON logging used by workflows and Lambda handlers."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from aspare.core.models import to_jsonable

_LOGGER_NAME = "aspare"


def get_logger(name: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name or _LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **{k: to_jsonable(v) for k, v in fields.items()}}
    logger.info(json.dumps(payload, default=str, sort_keys=True))
