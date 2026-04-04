"""
feedback.py - Routes for metrics ingestion and deterministic decision output.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import get_feedback_service
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
