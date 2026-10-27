"""UTC clock and timestamp helpers."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return utcnow()
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return utcnow()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
