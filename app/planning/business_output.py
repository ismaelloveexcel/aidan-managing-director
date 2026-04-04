"""
Business output engine – generates structured business_output.json payload.

Consolidates idea, evaluation, business package, distribution plan,
and deployment metadata into a single machine-readable output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


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
