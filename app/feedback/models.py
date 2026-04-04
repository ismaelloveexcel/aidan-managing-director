"""
Typed models for feedback ingestion and policy decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

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
    payment_attempted: bool = False
    payment_success: bool = False
    revenue_amount: float = Field(default=0.0, ge=0.0)

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
    payment_attempted: bool = False
    payment_success: bool = False
    revenue_amount: float = 0.0


class DecisionResult(BaseModel):
    """Deterministic policy output for a project."""

    decision: str
    reason: str
    next_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_next_state: str
    suggested_next_action: str
    evaluated_at: str = Field(default_factory=utcnow_iso)


# ---------------------------------------------------------------------------
# User feedback (rejection / objection) models
# ---------------------------------------------------------------------------


class UserFeedbackType(str, Enum):
    """Standard user feedback / rejection categories."""

    TOO_EXPENSIVE = "too_expensive"
    NOT_CLEAR = "not_clear"
    NOT_NEEDED = "not_needed"
    OTHER = "other"


class UserFeedbackAction(str, Enum):
    """Actions derived from user feedback."""

    ADJUST_PRICING = "adjust_pricing"
    IMPROVE_MESSAGING = "improve_messaging"
    DOWNGRADE_IDEA_SCORE = "downgrade_idea_score"
    LOG_OTHER = "log_other"


# Deterministic mapping from feedback to action.
FEEDBACK_ACTION_MAP: dict[UserFeedbackType, UserFeedbackAction] = {
    UserFeedbackType.TOO_EXPENSIVE: UserFeedbackAction.ADJUST_PRICING,
    UserFeedbackType.NOT_CLEAR: UserFeedbackAction.IMPROVE_MESSAGING,
    UserFeedbackType.NOT_NEEDED: UserFeedbackAction.DOWNGRADE_IDEA_SCORE,
    UserFeedbackType.OTHER: UserFeedbackAction.LOG_OTHER,
}


class UserFeedbackRequest(BaseModel):
    """Payload for user rejection / objection feedback."""

    project_id: str
    feedback_type: UserFeedbackType
    detail: str = ""

    @field_validator("project_id")
    @classmethod
    def _non_empty_pid(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("project_id must be a non-empty string.")
        return value.strip()


class UserFeedbackResponse(BaseModel):
    """Response after processing user feedback."""

    project_id: str
    feedback_type: UserFeedbackType
    mapped_action: UserFeedbackAction
    detail: str
    recorded_at: str = Field(default_factory=utcnow_iso)
