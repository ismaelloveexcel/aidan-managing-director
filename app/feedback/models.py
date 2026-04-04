"""
Typed models for feedback ingestion and policy decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def utcnow_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class MetricsIngestRequest(BaseModel):
    """Payload accepted by POST /feedback/metrics."""

    project_id: str
    visits: int = Field(ge=0)
    signups: int = Field(ge=0)
    revenue: float = Field(ge=0.0)
    currency: str = "USD"
    timestamp: str

    @field_validator("project_id", "currency", "timestamp")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Field must be a non-empty string.")
        return value.strip()


class MetricsIngestResponse(BaseModel):
    """Normalized metrics snapshot returned by feedback ingestion."""

    snapshot_id: str
    project_id: str
    visits: int
    signups: int
    revenue: float
    currency: str
    conversion_rate: float
    timestamp: str
    created_at: str


class DecisionResult(BaseModel):
    """Deterministic policy output for a project."""

    decision: str
    reason: str
    next_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_next_state: str
    suggested_next_action: str
    evaluated_at: str = Field(default_factory=utcnow_iso)
