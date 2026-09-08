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
