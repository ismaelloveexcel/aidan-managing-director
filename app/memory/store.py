"""
store.py - Lightweight memory and learning store for AI-DAN.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, Field


class LearningSignal(BaseModel):
    """Normalized learning signal captured from runtime outcomes."""

    project_id: str
    signal_type: str
    score: float = Field(ge=0.0, le=1.0)
    notes: str = ""


class MemoryStore:
    """In-memory memory/learning layer with deterministic behavior."""

    def __init__(self, max_events: int = 2000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._signals: deque[LearningSignal] = deque(maxlen=max_events)

    def record_event(self, event: dict[str, Any]) -> None:
        """Record a raw memory event."""
        self._events.append(dict(event))

    def record_signal(self, signal: LearningSignal) -> None:
        """Record a normalized learning signal."""
        self._signals.append(signal)

    def recent_events(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return recent memory events."""
        if limit <= 0:
            return []
        return list(self._events)[-limit:]

    def get_project_signals(self, project_id: str, limit: int = 50) -> list[LearningSignal]:
        """Return recent learning signals for a project."""
        matched = [signal for signal in self._signals if signal.project_id == project_id]
        if limit <= 0:
            return []
        return matched[-limit:]

    def summarize_project_learning(self, project_id: str) -> dict[str, Any]:
        """Aggregate project learning into deterministic summary metrics."""
        signals = self.get_project_signals(project_id, limit=10_000)
        if not signals:
            return {
                "project_id": project_id,
                "signal_count": 0,
                "average_score": 0.0,
                "top_signal_type": None,
            }

        by_type: dict[str, int] = {}
        total = 0.0
        for signal in signals:
            by_type[signal.signal_type] = by_type.get(signal.signal_type, 0) + 1
            total += signal.score

        top_signal_type = max(by_type, key=by_type.get)
        return {
            "project_id": project_id,
            "signal_count": len(signals),
            "average_score": round(total / len(signals), 2),
            "top_signal_type": top_signal_type,
        }

    def reset(self) -> None:
        """Clear all stored memory and learning records."""
        self._events.clear()
        self._signals.clear()
