"""
Outcome store for historical idea performance data.

Stores idea text alongside measured outcome metrics so the scoring
engine can incorporate aggregate stats from prior similar ideas
(PR #14 — outcome-weighted scoring feedback loop).

Similarity search uses Jaccard overlap on word sets, providing a
lightweight approximation of embedding-based similarity that works
without an external ML model while remaining deterministic and testable.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class OutcomeRecord(BaseModel):
    """A historical idea outcome entry."""

    idea_id: str
    idea_text: str
    outcome_score: float = Field(ge=0.0, le=1.0)  # normalised 0–1 (1 = best)
    revenue_usd: float = Field(default=0.0, ge=0.0)
    conversions: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    churn30d: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = "unknown"
    captured_at: str = Field(default_factory=_utcnow_iso)


class SimilarOutcome(BaseModel):
    """A retrieved similar outcome paired with its similarity score."""

    record: OutcomeRecord
    similarity: float = Field(ge=0.0, le=1.0)


class OutcomeStore:
    """In-memory store of historical idea outcomes with similarity search.

    Thread-safe for concurrent reads and writes.
    """

    def __init__(self) -> None:
        self._records: list[OutcomeRecord] = []
        self._lock = threading.Lock()

    def add_record(self, record: OutcomeRecord) -> None:
        """Append a new outcome record to the store."""
        with self._lock:
            self._records.append(record)

    def find_similar(
        self,
        text: str,
        *,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SimilarOutcome]:
        """Return the *top_k* most-similar historical outcomes.

        Similarity is measured as Jaccard overlap between word sets.

        Args:
            text: Query text (idea description or combined fields).
            top_k: Maximum number of neighbors to return.
            min_similarity: Only include neighbors at or above this threshold.

        Returns:
            Sorted list of :class:`SimilarOutcome` (highest similarity first).
        """
        with self._lock:
            records = list(self._records)

        if not records or not text.strip():
            return []

        scored: list[tuple[float, OutcomeRecord]] = []
        for record in records:
            sim = _jaccard_similarity(text, record.idea_text)
            if sim >= min_similarity:
                scored.append((sim, record))

        scored.sort(key=lambda t: t[0], reverse=True)

        return [
            SimilarOutcome(record=rec, similarity=sim)
            for sim, rec in scored[:top_k]
        ]

    def record_count(self) -> int:
        """Return the total number of stored outcome records."""
        with self._lock:
            return len(self._records)

    def reset(self) -> None:
        """Clear all stored records."""
        with self._lock:
            self._records.clear()


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between two texts based on word sets.

    Tokens are lowercased and stripped of punctuation before comparison.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Similarity in [0.0, 1.0]; 0.0 when either text is empty.
    """
    strip_chars = ".,;:!?()[]{}\"'"
    a = {w.strip(strip_chars).lower() for w in text_a.split() if w.strip(strip_chars)}
    b = {w.strip(strip_chars).lower() for w in text_b.split() if w.strip(strip_chars)}
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union > 0 else 0.0
