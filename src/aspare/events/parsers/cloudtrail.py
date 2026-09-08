"""Parse AWS CloudTrail management events delivered through EventBridge."""

from __future__ import annotations

from typing import Any

from aspare.core.enums import EventType, Provider, ResourceType
from aspare.core.ids import correlation_id
from aspare.core.models import StorageEvent
from aspare.core.timeutil import parse_timestamp, utcnow

_S3_EVENT_NAMES = {
    "CreateBucket",
    "PutBucketAcl",
    "PutBucketPolicy",
    "DeleteBucketPolicy",
    "PutBucketPublicAccessBlock",
    "DeletePublicAccessBlock",
    "PutBucketEncryption",
    "DeleteBucketEncryption",
    "PutBucketVersioning",
    "PutBucketOwnershipControls",
    "PutObjectAcl",
}


def parse_cloudtrail(raw: dict[str, Any]) -> StorageEvent | None:
    detail = raw.get("detail") or {}
    event_source = detail.get("eventSource") or raw.get("source")
    if event_source not in {"s3.amazonaws.com", "aws.s3"} and raw.get("source") not in {
        "aws.s3",
        "aws.cloudtrail",
    }:
        return None

    params = detail.get("requestParameters") or {}
    bucket = (
        params.get("bucketName")
        or params.get("bucket")
        or (params.get("Host") if isinstance(params.get("Host"), str) else None)
    )
    if not bucket:
        return None

    event_id = str(raw.get("id") or detail.get("eventID") or f"ct-{bucket}")
    actor = (
        (detail.get("userIdentity") or {}).get("arn")
        or (detail.get("userIdentity") or {}).get("principalId")
        or "unknown"
    )
    timestamp = parse_timestamp(detail.get("eventTime") or raw.get("time"))
    region = str(detail.get("awsRegion") or raw.get("region") or "us-east-1")
    return StorageEvent(
        event_id=event_id,
        provider=Provider.AWS,
        event_type=EventType.CLOUDTRAIL_API_CALL,
        resource_type=ResourceType.S3_BUCKET,
        resource_id=str(bucket),
        actor=str(actor),
        timestamp=timestamp or utcnow(),
        region=region,
        correlation_id=correlation_id(event_id),
        metadata={
            "event_name": detail.get("eventName"),
            "event_source": event_source,
            "request_parameters": {
                key: value
                for key, value in params.items()
                if key in {"bucketName", "PublicAccessBlockConfiguration", "x-amz-acl"}
            },
            "handled_event": detail.get("eventName") in _S3_EVENT_NAMES,
        },
    )
