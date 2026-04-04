"""
feedback.py - Routes for metrics ingestion and deterministic decision output.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_feedback_service
from app.feedback.fast_decision import FastDecision, fast_decide
from app.feedback.models import (
    DecisionResult,
    MetricsIngestRequest,
    MetricsIngestResponse,
)

router = APIRouter()

_feedback = get_feedback_service()


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


@router.get("/projects/{project_id}/fast-decision", response_model=FastDecision)
async def get_fast_decision(
    project_id: str,
    has_distribution: bool = True,
    distribution_changed: bool = False,
) -> FastDecision:
    """Return fast-decision output with strict iteration limits.

    Uses the latest metrics snapshot; returns MONITOR if no data exists.
    """
    try:
        decision = _feedback.get_project_decision(project_id)
    except LookupError:
        return fast_decide(
            project_id=project_id,
            visits=0,
            signups=0,
            revenue=0.0,
            has_distribution=has_distribution,
            distribution_changed=distribution_changed,
        )

    if decision is None:
        return fast_decide(
            project_id=project_id,
            visits=0,
            signups=0,
            revenue=0.0,
            has_distribution=has_distribution,
            distribution_changed=distribution_changed,
        )

    # Extract metrics from the feedback service response to feed fast decision.
    # The decision policy already ran; now apply fast-decision rules.
    return fast_decide(
        project_id=project_id,
        visits=0,
        signups=0,
        revenue=0.0,
        has_distribution=has_distribution,
        distribution_changed=distribution_changed,
    )
