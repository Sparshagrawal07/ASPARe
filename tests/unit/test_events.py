import json
from pathlib import Path

from aspare.core.enums import EventType, Provider
from aspare.events.normalizer import EventNormalizer


def test_cloudtrail_normalization(repo_root: Path):
    raw = json.loads((repo_root / "tests" / "fixtures" / "cloudtrail_put_pab.json").read_text())
    event = EventNormalizer().normalize(raw)
    assert event.provider is Provider.AWS
    assert event.event_type is EventType.CLOUDTRAIL_API_CALL
    assert event.resource_id == "demo-bucket"
    assert "aspare-tester" in event.actor
    assert event.metadata["event_name"] == "PutBucketPublicAccessBlock"


def test_scheduled_scan_expands_buckets():
    events = EventNormalizer().normalize(
        {
            "id": "sched-1",
            "source": "aspare.scheduler",
            "detail-type": "ASPARe Scheduled Inventory Scan",
            "detail": {"buckets": ["a", "b"], "actor": "scheduler"},
        }
    )
    assert isinstance(events, list)
    assert [item.resource_id for item in events] == ["a", "b"]
    assert events[0].event_type is EventType.SCHEDULED_SCAN


def test_demo_event_normalization():
    event = EventNormalizer().normalize(
        {
            "source": "aspare.demo",
            "detail-type": "ASPARe Direct Scan",
            "detail": {"bucket": "demo-bucket", "actor": "demo"},
        }
    )
    assert event.resource_id == "demo-bucket"
    assert event.event_type is EventType.DEMO
