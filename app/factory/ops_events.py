"""
ops_events.py – Lightweight operational event tracking for SLO metrics.

Records dispatch, callback, and deployment events with success/failure
and latency so the solo founder can see system health at a glance.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpsEvent(BaseModel):
    """A single operational event for SLO tracking."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # dispatch | callback | deployment | readiness_check
    correlation_id: str | None = None
    project_id: str | None = None
    success: bool
    latency_ms: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utcnow_iso)


class OpsEventStore:
    """Persistent ops-event store backed by the portfolio DB."""

    def __init__(self, db_connect: Any) -> None:
        self._db_connect = db_connect

    def record(self, event: OpsEvent) -> None:
        """Persist an operational event."""
        with self._db_connect() as conn:
            conn.execute(
                """
                INSERT INTO ops_events
                (event_id, event_type, correlation_id, project_id,
                 success, latency_ms, error, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.correlation_id,
                    event.project_id,
                    1 if event.success else 0,
                    event.latency_ms,
                    event.error,
                    json.dumps(event.metadata),
                    event.created_at,
                ),
            )

    def slo_summary(self, hours: int = 24) -> dict[str, Any]:
        """Compute SLO metrics over the last N hours.

        Returns:
            Dictionary with per-event-type success rate, counts, and
            average latency.
        """
        with self._db_connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type,
                       COUNT(*) as total,
                       SUM(success) as successes,
                       AVG(latency_ms) as avg_latency_ms
                FROM ops_events
                WHERE created_at >= datetime('now', ?)
                GROUP BY event_type
                """,
                (f"-{hours} hours",),
            ).fetchall()

        summary: dict[str, Any] = {
            "window_hours": hours,
            "event_types": {},
        }
        for row in rows:
            event_type = row[0]
            total = row[1]
            successes = row[2] or 0
            avg_latency = row[3]
            summary["event_types"][event_type] = {
                "total": total,
                "successes": successes,
                "failures": total - successes,
                "success_rate": round(successes / total, 4) if total else 0.0,
                "avg_latency_ms": round(avg_latency, 2) if avg_latency else None,
            }
        return summary

    def stuck_jobs(self, max_age_minutes: int = 30) -> list[dict[str, Any]]:
        """Find dispatched runs with no callback within the time window."""
        with self._db_connect() as conn:
            rows = conn.execute(
                """
                SELECT e.correlation_id, e.project_id, e.created_at
                FROM ops_events e
                WHERE e.event_type = 'dispatch'
                  AND e.success = 1
                  AND e.created_at <= datetime('now', ?)
                  AND NOT EXISTS (
                      SELECT 1 FROM ops_events cb
                      WHERE cb.event_type = 'callback'
                        AND cb.correlation_id = e.correlation_id
                  )
                ORDER BY e.created_at ASC
                LIMIT 50
                """,
                (f"-{max_age_minutes} minutes",),
            ).fetchall()
        return [
            {
                "correlation_id": row[0],
                "project_id": row[1],
                "dispatched_at": row[2],
            }
            for row in rows
        ]

    def reset(self) -> None:
        """Clear all events (for tests)."""
        with self._db_connect() as conn:
            conn.execute("DELETE FROM ops_events")
