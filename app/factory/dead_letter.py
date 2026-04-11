"""
dead_letter.py – Dead-letter queue for failed factory callbacks.

Failed callbacks are stored, retried up to ``max_retries`` times,
and surfaced via an operator endpoint so the solo founder can see
and recover from failures without digging through logs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeadLetterEntry(BaseModel):
    """A single entry in the dead-letter queue."""

    dlq_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    project_id: str
    payload: dict[str, Any]
    error: str
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending | retrying | exhausted | resolved
    created_at: str = Field(default_factory=_utcnow_iso)
    last_retry_at: str | None = None


class DeadLetterQueue:
    """Persistent dead-letter queue backed by the portfolio DB."""

    def __init__(self, db_connect: Any) -> None:
        """Accept a callable that returns a DB connection context manager."""
        self._db_connect = db_connect

    def enqueue(self, entry: DeadLetterEntry) -> None:
        """Add a failed callback to the dead-letter queue."""
        with self._db_connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dead_letter_callbacks
                (dlq_id, correlation_id, project_id, payload_json, error,
                 retry_count, max_retries, status, created_at, last_retry_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.dlq_id,
                    entry.correlation_id,
                    entry.project_id,
                    json.dumps(entry.payload),
                    entry.error,
                    entry.retry_count,
                    entry.max_retries,
                    entry.status,
                    entry.created_at,
                    entry.last_retry_at,
                ),
            )

    def list_pending(self, limit: int = 50) -> list[DeadLetterEntry]:
        """Return pending entries ordered oldest-first."""
        with self._db_connect() as conn:
            rows = conn.execute(
                """
                SELECT dlq_id, correlation_id, project_id, payload_json,
                       error, retry_count, max_retries, status,
                       created_at, last_retry_at
                FROM dead_letter_callbacks
                WHERE status IN ('pending', 'retrying')
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._to_entry(row) for row in rows]

    def list_all(self, limit: int = 100) -> list[DeadLetterEntry]:
        """Return all entries (any status) ordered newest-first."""
        with self._db_connect() as conn:
            rows = conn.execute(
                """
                SELECT dlq_id, correlation_id, project_id, payload_json,
                       error, retry_count, max_retries, status,
                       created_at, last_retry_at
                FROM dead_letter_callbacks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._to_entry(row) for row in rows]

    def mark_retrying(self, dlq_id: str) -> None:
        """Increment retry count and mark as retrying."""
        now = _utcnow_iso()
        with self._db_connect() as conn:
            conn.execute(
                """
                UPDATE dead_letter_callbacks
                SET retry_count = retry_count + 1,
                    status = CASE
                        WHEN retry_count + 1 >= max_retries THEN 'exhausted'
                        ELSE 'retrying'
                    END,
                    last_retry_at = ?
                WHERE dlq_id = ?
                """,
                (now, dlq_id),
            )

    def mark_resolved(self, dlq_id: str) -> None:
        """Mark an entry as resolved (successfully retried)."""
        with self._db_connect() as conn:
            conn.execute(
                "UPDATE dead_letter_callbacks SET status = 'resolved' WHERE dlq_id = ?",
                (dlq_id,),
            )

    def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status."""
        with self._db_connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM dead_letter_callbacks GROUP BY status"
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def reset(self) -> None:
        """Clear all entries (for tests)."""
        with self._db_connect() as conn:
            conn.execute("DELETE FROM dead_letter_callbacks")

    @staticmethod
    def _to_entry(row: Any) -> DeadLetterEntry:
        return DeadLetterEntry(
            dlq_id=row[0],
            correlation_id=row[1],
            project_id=row[2],
            payload=json.loads(row[3]),
            error=row[4],
            retry_count=row[5],
            max_retries=row[6],
            status=row[7],
            created_at=row[8],
            last_retry_at=row[9],
        )
