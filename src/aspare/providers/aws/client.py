"""Shared boto3 client construction."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.client import BaseClient


def s3_client(region: str | None = None, session: Any | None = None) -> BaseClient:
    if session is not None:
        return session.client("s3", region_name=region)
    if region:
        return boto3.client("s3", region_name=region)
    return boto3.client("s3")
