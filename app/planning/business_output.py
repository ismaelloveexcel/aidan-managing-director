"""
business_output.py – Structured business output for revenue intelligence layer.

Produces a deterministic ``BusinessOutput`` that aggregates payment,
pricing, feedback, and conversion status into a single machine-readable
report.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.feedback.models import DecisionResult, UserFeedbackType, utcnow_iso


class FeedbackSummary(BaseModel):
    """Aggregated summary of user feedback for a project."""

    total_feedback_count: int = 0
    too_expensive_count: int = 0
    not_clear_count: int = 0
    not_needed_count: int = 0
    other_count: int = 0
    dominant_feedback: str | None = None


class BusinessOutput(BaseModel):
    """Complete business output snapshot for a project."""

    project_id: str
    payment_link: str | None = None
    pricing_strategy: str = "default"
    feedback_summary: FeedbackSummary = Field(default_factory=FeedbackSummary)
    conversion_status: str = "unknown"
    latest_decision: DecisionResult | None = None
    generated_at: str = Field(default_factory=utcnow_iso)


def build_business_output(
    *,
    project_id: str,
    payment_link: str | None = None,
    pricing_strategy: str = "default",
    feedback_counts: dict[str, int] | None = None,
    conversion_status: str = "unknown",
    latest_decision: DecisionResult | None = None,
) -> BusinessOutput:
    """Construct a ``BusinessOutput`` from available project data."""
    counts = feedback_counts or {}

    too_expensive = counts.get(UserFeedbackType.TOO_EXPENSIVE.value, 0) + counts.get(
        "user_feedback_too_expensive", 0,
    )
    not_clear = counts.get(UserFeedbackType.NOT_CLEAR.value, 0) + counts.get(
        "user_feedback_not_clear", 0,
    )
    not_needed = counts.get(UserFeedbackType.NOT_NEEDED.value, 0) + counts.get(
        "user_feedback_not_needed", 0,
    )
    other = counts.get(UserFeedbackType.OTHER.value, 0) + counts.get(
        "user_feedback_other", 0,
    )
    total = too_expensive + not_clear + not_needed + other

    dominant: str | None = None
    if total > 0:
        mapping = {
            "too_expensive": too_expensive,
            "not_clear": not_clear,
            "not_needed": not_needed,
            "other": other,
        }
        dominant = max(mapping, key=mapping.get)  # type: ignore[arg-type]

    summary = FeedbackSummary(
        total_feedback_count=total,
        too_expensive_count=too_expensive,
        not_clear_count=not_clear,
        not_needed_count=not_needed,
        other_count=other,
        dominant_feedback=dominant,
    )

    # Derive pricing_strategy from feedback if not explicitly provided.
    if pricing_strategy == "default" and too_expensive >= 3:
        pricing_strategy = "reduce"
    if pricing_strategy == "default" and latest_decision and latest_decision.decision == "scale_candidate":
        pricing_strategy = "hold"

    return BusinessOutput(
        project_id=project_id,
        payment_link=payment_link,
        pricing_strategy=pricing_strategy,
        feedback_summary=summary,
        conversion_status=conversion_status,
        latest_decision=latest_decision,
    )
