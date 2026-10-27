"""Behavioural anomaly scoring over the storage change events ASPARe actually observes.

Every signal is computed from real evidence in the event stream (who changed what, when, how often) against a
baseline learned from the events seen so far. A signal that cannot be computed (no history, no event) is omitted
instead of guessed, and the combined score is only reported when at least one signal exists.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from aspare.config.paths import config_dir
from aspare.core.models import StorageEvent


@dataclass(frozen=True)
class Signal:
    name: str
    value: float  # 0..1
    explanation: str


@dataclass
class AnomalyAssessment:
    score: float | None  # None = no behavioural evidence (e.g. scheduled scan)
    signals: list[Signal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "signals": [
                {"name": s.name, "value": round(s.value, 3), "explanation": s.explanation} for s in self.signals
            ],
        }


def load_fusion_policy(path: str | Path | None = None) -> dict[str, Any]:
    return json.loads(Path(path or config_dir() / "fusion-policy.json").read_text(encoding="utf-8"))


class AnomalyDetector:
    def __init__(self, policy: dict[str, Any] | None = None, max_history: int = 5000) -> None:
        cfg = (policy or load_fusion_policy())["anomaly"]
        self._cfg = cfg
        self._history: deque[StorageEvent] = deque(maxlen=max_history)
        self._actor_hours: dict[str, list[int]] = defaultdict(list)

    def observe(self, event: StorageEvent) -> None:
        """Add an event to the learned baseline (call after assessing it)."""
        self._history.append(event)
        self._actor_hours[event.actor].append(event.timestamp.hour)

    def bootstrap(self, events: list[StorageEvent]) -> None:
        for event in events:
            self.observe(event)

    def assess(self, event: StorageEvent | None) -> AnomalyAssessment:
        name = (event.metadata.get("event_name") if event else None) or None
        if event is None or not name:
            return AnomalyAssessment(score=None)
        signals: list[Signal] = []
        weights = self._cfg["signal_weights"]

        if ":root" in event.actor or event.actor.endswith("root"):
            signals.append(
                Signal(
                    "privileged_actor",
                    1.0,
                    "Change made with root credentials, which should never be used for routine work.",
                )
            )

        risk = self._cfg["action_risk"].get(str(name))
        if risk is not None:
            params = event.metadata.get("request_parameters") or {}
            pab = params.get("PublicAccessBlockConfiguration")
            if name == "PutBucketPublicAccessBlock" and isinstance(pab, dict):
                off = sum(1 for v in pab.values() if v is False)
                risk = 0.35 + 0.65 * (off / 4)  # a 4/4-off write is a deliberate disable, not a tweak
            signals.append(Signal("risky_action", float(risk), f"{name} can weaken the bucket's security posture."))

        burst = self._burst(event)
        if burst:
            signals.append(burst)

        novelty = self._novelty(event)
        if novelty:
            signals.append(novelty)

        hours = self._off_hours(event)
        if hours:
            signals.append(hours)

        if not signals:
            return AnomalyAssessment(score=0.0)
        remaining = 1.0
        for signal in signals:
            remaining *= 1.0 - weights.get(signal.name, 0.3) * signal.value
        return AnomalyAssessment(score=round(1.0 - remaining, 4), signals=signals)

    # --- signals ---------------------------------------------------------------------------------------------
    def _burst(self, event: StorageEvent) -> Signal | None:
        window = timedelta(minutes=int(self._cfg["burst_window_minutes"]))
        risky = set(self._cfg["action_risk"]) - {"CreateBucket"}
        recent = [
            h
            for h in self._history
            if h.actor == event.actor
            and h.metadata.get("event_name") in risky
            and abs(event.timestamp - h.timestamp) <= window
        ]
        count = len(recent) + 1
        if count < int(self._cfg["burst_min_events"]):
            return None
        buckets = len({h.resource_id for h in recent} | {event.resource_id})
        value = min(1.0, 0.3 + 0.2 * (count - int(self._cfg["burst_min_events"]) + 1))
        return Signal(
            "burst",
            value,
            f"{count} security-relevant changes by the same actor within "
            f"{int(self._cfg['burst_window_minutes'])} minutes across {buckets} bucket(s).",
        )

    def _novelty(self, event: StorageEvent) -> Signal | None:
        if len(self._history) < int(self._cfg["min_history_for_novelty"]):
            return None
        if any(h.actor == event.actor for h in self._history):
            return None
        return Signal("novel_actor", 1.0, "First time this actor appears in the observed change history.")

    def _off_hours(self, event: StorageEvent) -> Signal | None:
        hour = event.timestamp.hour
        samples = self._actor_hours.get(event.actor, [])
        if len(samples) >= int(self._cfg["min_events_for_hour_profile"]):
            seen = {h for h in samples}
            if hour not in seen:
                return Signal(
                    "off_hours", 1.0, f"Hour {hour:02d}:00 UTC is outside this actor's learned activity pattern."
                )
            return None
        start, end = self._cfg["default_active_hours_utc"]
        if not start <= hour < end:
            return Signal("off_hours", 0.7, f"Hour {hour:02d}:00 UTC is outside default working hours ({start}-{end}).")
        return None
