"""
feedback.py - Routes for metrics ingestion, user feedback, and deterministic decision output.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_feedback_service, get_portfolio_repository
from app.feedback.fast_decision import FastDecision, fast_decide
from app.feedback.models import (
    DecisionResult,
    MetricsIngestRequest,
    MetricsIngestResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
)

router = APIRouter()

_feedback = get_feedback_service()
_portfolio = get_portfolio_repository()


@router.post("/metrics", response_model=MetricsIngestResponse)
async def ingest_metrics(payload: MetricsIngestRequest) -> MetricsIngestResponse:
    """Ingest and normalize product metrics for a project."""
    try:
        return _feedback.ingest_metrics(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/projects/{project_id}/decision", response_model=DecisionResult)
async def get_project_decision(project_id: str) -> DecisionResult:
    """Return deterministic decision output for the latest project metrics."""
    try:
        decision = _feedback.get_project_decision(project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if decision is None:
        raise HTTPException(status_code=404, detail="No metrics found for project")
    return decision


def _default_fast_decision(
    project_id: str,
    has_distribution: bool,
    distribution_changed: bool,
) -> FastDecision:
    """Return a fast decision with zero metrics (no data available)."""
    return fast_decide(
        project_id=project_id,
        visits=0,
        signups=0,
        revenue=0.0,
        has_distribution=has_distribution,
        distribution_changed=distribution_changed,
    )


@router.get("/projects/{project_id}/fast-decision", response_model=FastDecision)
async def get_fast_decision(
    project_id: str,
    has_distribution: bool = True,
    distribution_changed: bool = False,
) -> FastDecision:
    """Return fast-decision output with strict iteration limits.

    Uses the latest metrics snapshot to feed the fast-decision engine.
    When no snapshot exists the engine receives zero metrics and will
    return CHANGE_DISTRIBUTION or MONITOR depending on distribution state.
    """
    snapshot = _portfolio.get_latest_metrics_snapshot(project_id)
    if snapshot is None:
        return _default_fast_decision(project_id, has_distribution, distribution_changed)

    return fast_decide(
        project_id=project_id,
        visits=snapshot.visits,
        signups=snapshot.signups,
        revenue=snapshot.revenue,
        has_distribution=has_distribution,
        distribution_changed=distribution_changed,
    )


@router.post("/user-feedback", response_model=UserFeedbackResponse)
async def submit_user_feedback(payload: UserFeedbackRequest) -> UserFeedbackResponse:
    """Process user rejection / objection feedback and map to action."""
    try:
        return _feedback.process_user_feedback(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
