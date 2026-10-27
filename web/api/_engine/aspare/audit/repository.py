"""Audit record construction and repository implementations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aspare.core.enums import AuditAction
from aspare.core.ids import record_id
from aspare.core.interfaces import AuditRepository
from aspare.core.models import AuditRecord, Finding, to_jsonable
from aspare.core.timeutil import utcnow
from aspare.logging import get_logger, log_event


class AuditPersistenceError(RuntimeError):
    pass


def build_record(
    *,
    action: str,
    result: str,
    resource_id: str,
    correlation_id: str,
    finding: Finding | None = None,
    verified: bool | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    actor: str | None = None,
    event_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditRecord:
    return AuditRecord(
        record_id=record_id(),
        timestamp=utcnow(),
        resource_id=resource_id,
        action=action,
        result=result,
        correlation_id=correlation_id,
        finding_id=finding.finding_id if finding else None,
        rule_id=finding.rule_id if finding else None,
        policy_id=finding.policy_id if finding else None,
        severity=finding.severity if finding else None,
        verified=verified,
        before_state=before_state or (finding.before_state if finding else {}),
        after_state=after_state or {},
        actor=actor,
        event_id=event_id or (finding.event_id if finding else None),
        details=details or {},
    )


class MemoryAuditRepository:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def list_records(self) -> list[AuditRecord]:
        return list(self._records)


class JsonlAuditRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: AuditRecord) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        except OSError as exc:
            raise AuditPersistenceError(str(exc)) from exc

    def list_records(self) -> list[AuditRecord]:
        if not self.path.exists():
            return []
        records: list[AuditRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(AuditRecord.from_dict(json.loads(line)))
        return records


class S3AuditRepository:
    def __init__(self, client: Any, bucket: str, prefix: str = "audit/") -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/"

    def append(self, record: AuditRecord) -> None:
        key = f"{self._prefix}{record.timestamp.strftime('%Y/%m/%d')}/{record.record_id}.json"
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=json.dumps(record.to_dict(), indent=2, sort_keys=True).encode("utf-8"),
                ContentType="application/json",
            )
        except Exception as exc:  # noqa: BLE001
            raise AuditPersistenceError(str(exc)) from exc

    def list_records(self) -> list[AuditRecord]:
        records: list[AuditRecord] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": self._bucket, "Prefix": self._prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self._client.list_objects_v2(**kwargs)
            for item in response.get("Contents") or []:
                body = self._client.get_object(Bucket=self._bucket, Key=item["Key"])["Body"].read()
                records.append(AuditRecord.from_dict(json.loads(body)))
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return records


class FallbackAuditRepository:
    """Write to the primary store; on failure log to stdout/CloudWatch and re-raise."""

    def __init__(self, primary: AuditRepository) -> None:
        self._primary = primary
        self._logger = get_logger("aspare.audit")

    def append(self, record: AuditRecord) -> None:
        try:
            self._primary.append(record)
        except Exception as exc:  # noqa: BLE001
            log_event(
                self._logger,
                AuditAction.AUDIT_FALLBACK.value,
                error=str(exc),
                record=to_jsonable(record),
            )
            raise AuditPersistenceError(str(exc)) from exc

    def list_records(self) -> list[AuditRecord]:
        return self._primary.list_records()
