"""Parse scheduled inventory scan events."""

from __future__ import annotations

from typing import Any

from aspare.core.enums import EventType, Provider, ResourceType
from aspare.core.ids import correlation_id
from aspare.core.models import StorageEvent
from aspare.core.timeutil import parse_timestamp, utcnow


def parse_scheduled(raw: dict[str, Any]) -> list[StorageEvent]:
    detail = raw.get("detail") or {}
    buckets = detail.get("buckets") or detail.get("resource_ids") or []
    event_id = str(raw.get("id") or "scheduled-scan")
    actor = str(detail.get("actor") or "aspare.scheduler")
    timestamp = parse_timestamp(raw.get("time") or detail.get("timestamp"))
    region = str(detail.get("region") or raw.get("region") or "us-east-1")
    if not buckets:
        return [
            StorageEvent(
                event_id=event_id,
                provider=Provider.AWS,
                event_type=EventType.SCHEDULED_SCAN,
                resource_type=ResourceType.S3_BUCKET,
                resource_id="*",
                actor=actor,
                timestamp=timestamp or utcnow(),
                region=region,
                correlation_id=correlation_id(event_id),
                metadata={"scan_scope": "allowlist"},
            )
        ]
    events: list[StorageEvent] = []
    for bucket in buckets:
        eid = f"{event_id}:{bucket}"
        events.append(
            StorageEvent(
                event_id=eid,
                provider=Provider.AWS,
                event_type=EventType.SCHEDULED_SCAN,
                resource_type=ResourceType.S3_BUCKET,
                resource_id=str(bucket),
                actor=actor,
                timestamp=timestamp or utcnow(),
                region=region,
                correlation_id=correlation_id(event_id),
                metadata={"scan_scope": "explicit"},
            )
        )
    return events
