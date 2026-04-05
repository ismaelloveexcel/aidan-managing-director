"""
Business output engines for AI-DAN.

1. Idea business output (``generate_business_output``):
   Generates a structured business_output.json payload consolidating idea,
   evaluation, business package, distribution plan, and deployment metadata.

2. Revenue business output (``build_revenue_business_output``):
   Produces a deterministic ``RevenueBusinessOutput`` that aggregates
   payment, pricing, feedback, and conversion status into a single
   machine-readable report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.feedback.models import DecisionResult, UserFeedbackType, utcnow_iso


# ======================================================================
# Idea business output (original)
# ======================================================================


class BusinessOutput(BaseModel):
    """Canonical business output document for a validated, approved idea."""

    schema_version: str = "1.0"
    project_id: str
    idea_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Idea summary
    title: str
    problem: str
    target_user: str
    solution: str

    # Evaluation
    total_score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    decision: str

    # Business package
    offer: str
    pricing_model: str
    price_range: str
    landing_page: dict[str, str] = Field(default_factory=dict)
    gtm_strategy: list[str] = Field(default_factory=list)

    # Distribution
    primary_channel: str = ""
    first_10_users_plan: str = ""

    # Deployment
    repo_url: str | None = None
    deploy_url: str | None = None

    # Status
    status: str = "generated"


def generate_business_output(
    *,
    project_id: str,
    idea_id: str,
    idea: dict[str, Any],
    evaluation: dict[str, Any],
    business_package: dict[str, Any],
    distribution: dict[str, Any] | None = None,
    deployment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a complete business_output.json payload.

    Args:
        project_id: Unique project identifier.
        idea_id: Unique idea identifier.
        idea: Dict with title, problem, target_user, solution.
        evaluation: Dict with total_score, breakdown, decision.
        business_package: Dict with offer, pricing_model, price_range, landing_page, gtm_strategy.
        distribution: Optional dict with primary_channel, first_10_users_plan.
        deployment: Optional dict with repo_url, deploy_url.

    Returns:
        Serialised BusinessOutput as a dictionary.
    """
    dist = distribution or {}
    deploy = deployment or {}

    output = BusinessOutput(
        project_id=project_id,
        idea_id=idea_id,
        title=str(idea.get("title", "")),
        problem=str(idea.get("problem", "")),
        target_user=str(idea.get("target_user", "")),
        solution=str(idea.get("solution", "")),
        total_score=float(evaluation.get("total_score", 0.0)),
        score_breakdown=evaluation.get("breakdown", {}),
        decision=str(evaluation.get("decision", "")),
        offer=str(business_package.get("offer", "")),
        pricing_model=str(business_package.get("pricing_model", "")),
        price_range=str(business_package.get("price_range", "")),
        landing_page=business_package.get("landing_page", {}),
        gtm_strategy=business_package.get("gtm_strategy", []),
        primary_channel=str(dist.get("primary_channel", "")),
        first_10_users_plan=str(dist.get("first_10_users_plan", "")),
        repo_url=deploy.get("repo_url"),
        deploy_url=deploy.get("deploy_url"),
    )
    return output.model_dump(mode="json")


# ======================================================================
# Revenue business output (revenue intelligence layer)
# ======================================================================


class FeedbackSummary(BaseModel):
    """Aggregated summary of user feedback for a project."""

    total_feedback_count: int = 0
    too_expensive_count: int = 0
    not_clear_count: int = 0
    not_needed_count: int = 0
    other_count: int = 0
    dominant_feedback: str | None = None


class RevenueBusinessOutput(BaseModel):
    """Complete business output snapshot for a project (revenue intelligence)."""

    project_id: str
    payment_link: str | None = None
    pricing_strategy: str = "default"
    feedback_summary: FeedbackSummary = Field(default_factory=FeedbackSummary)
    conversion_status: str = "unknown"
    latest_decision: DecisionResult | None = None
    generated_at: str = Field(default_factory=utcnow_iso)


def build_revenue_business_output(
    *,
    project_id: str,
    payment_link: str | None = None,
    pricing_strategy: str = "default",
    feedback_counts: dict[str, int] | None = None,
    conversion_status: str = "unknown",
    latest_decision: DecisionResult | None = None,
) -> RevenueBusinessOutput:
    """Construct a ``RevenueBusinessOutput`` from available project data."""
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
        dominant = max(mapping, key=lambda k: mapping[k])

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

    return RevenueBusinessOutput(
        project_id=project_id,
        payment_link=payment_link,
        pricing_strategy=pricing_strategy,
        feedback_summary=summary,
        conversion_status=conversion_status,
        latest_decision=latest_decision,
    )
