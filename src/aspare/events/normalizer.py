"""Normalize CloudTrail, scheduled, and direct-scan events into StorageEvent."""

from __future__ import annotations

from typing import Any

from aspare.core.enums import EventType, Provider, ResourceType
from aspare.core.ids import correlation_id
from aspare.core.models import StorageEvent
from aspare.core.timeutil import utcnow
from aspare.events.parsers.cloudtrail import parse_cloudtrail
from aspare.events.parsers.demo import parse_demo
from aspare.events.parsers.scheduled import parse_scheduled


class EventNormalizationError(ValueError):
    pass


class EventNormalizer:
    def normalize(self, raw: dict[str, Any]) -> StorageEvent | list[StorageEvent]:
        source = str(raw.get("source") or "")
        detail_type = str(raw.get("detail-type") or raw.get("detailType") or "")

        if source in {"aws.s3", "aws.cloudtrail"} or detail_type == "AWS API Call via CloudTrail":
            event = parse_cloudtrail(raw)
            if event is None:
                raise EventNormalizationError("CloudTrail event did not contain an S3 bucket target")
            return event
        if source == "aspare.scheduler" or "Scheduled" in detail_type:
            return parse_scheduled(raw)
        if source in {"aspare.demo", "aspare.direct"} or "Direct" in detail_type or "Demo" in detail_type:
            return parse_demo(raw)
        if "bucket" in (raw.get("detail") or {}) or raw.get("bucket"):
            return parse_demo(raw)
        raise EventNormalizationError(f"Unsupported event source '{source}' / '{detail_type}'")

    def normalize_many(self, raw: dict[str, Any]) -> list[StorageEvent]:
        result = self.normalize(raw)
        if isinstance(result, list):
            return result
        return [result]


def fallback_event(resource_id: str, actor: str = "aspare") -> StorageEvent:
    now = utcnow()
    eid = f"direct-{resource_id}"
    return StorageEvent(
        event_id=eid,
        provider=Provider.AWS,
        event_type=EventType.DIRECT_SCAN,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=resource_id,
        actor=actor,
        timestamp=now,
        region="us-east-1",
        correlation_id=correlation_id(eid),
        metadata={"origin": "fallback"},
    )
