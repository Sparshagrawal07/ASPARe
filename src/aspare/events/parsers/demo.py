"""Parse direct/demo scan requests."""

from __future__ import annotations

from typing import Any

from aspare.core.enums import EventType, Provider, ResourceType
from aspare.core.ids import correlation_id
from aspare.core.models import StorageEvent
from aspare.core.timeutil import parse_timestamp, utcnow


def parse_demo(raw: dict[str, Any]) -> StorageEvent:
    detail = raw.get("detail") if isinstance(raw.get("detail"), dict) else raw
    bucket = str(detail.get("bucket") or detail.get("resource_id") or raw.get("bucket") or "")
    if not bucket:
        raise ValueError("Direct/demo event is missing a bucket/resource_id")
    event_id = str(raw.get("id") or detail.get("event_id") or f"demo-{bucket}")
    actor = str(detail.get("actor") or raw.get("actor") or "aspare.demo")
    timestamp = parse_timestamp(raw.get("time") or detail.get("timestamp"))
    region = str(detail.get("region") or raw.get("region") or "us-east-1")
    event_type = EventType.DEMO if (raw.get("source") == "aspare.demo") else EventType.DIRECT_SCAN
    return StorageEvent(
        event_id=event_id,
        provider=Provider.AWS,
        event_type=event_type,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=bucket,
        actor=actor,
        timestamp=timestamp or utcnow(),
        region=region,
        correlation_id=correlation_id(event_id),
        metadata={"origin": raw.get("source") or "direct"},
    )
