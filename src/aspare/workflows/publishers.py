"""Finding publishers used after risk classification."""

from __future__ import annotations

import json
from typing import Any

from aspare.core.models import Finding


class InProcessPublisher:
    """Collect AUTO_REMEDIATE findings for local/demo pipelines."""

    def __init__(self) -> None:
        self.published: list[Finding] = []

    def publish(self, finding: Finding) -> None:
        self.published.append(finding)


class EventBridgePublisher:
    def __init__(self, client: Any, bus_name: str, source: str = "aspare.detection") -> None:
        self._client = client
        self._bus_name = bus_name
        self._source = source

    def publish(self, finding: Finding) -> None:
        self._client.put_events(
            Entries=[
                {
                    "Source": self._source,
                    "DetailType": "ASPARe Finding For Remediation",
                    "Detail": json.dumps(finding.to_dict()),
                    "EventBusName": self._bus_name,
                }
            ]
        )


class NoOpPublisher:
    def publish(self, finding: Finding) -> None:
        return None


class SnsAlerter:
    """Notify humans about findings ASPARe will not auto-remediate."""

    def __init__(self, client: Any, topic_arn: str) -> None:
        self._client = client
        self._topic_arn = topic_arn

    def alert(self, finding: Finding) -> None:
        subject = f"[ASPARe][{finding.severity.value}] {finding.title} - {finding.resource_id}"
        self._client.publish(
            TopicArn=self._topic_arn,
            Subject=subject[:100],
            Message=json.dumps(
                {
                    "resource": finding.resource_id,
                    "rule": finding.rule_id,
                    "severity": finding.severity.value,
                    "description": finding.description,
                    "decision": finding.decision.value if finding.decision else None,
                    "finding_id": finding.finding_id,
                    "detected_at": finding.detected_at.isoformat(),
                },
                indent=2,
            ),
        )
