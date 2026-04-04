"""
intelligence.py - Portfolio intelligence endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_portfolio_intelligence_service

router = APIRouter()

_intelligence = get_portfolio_intelligence_service()


class ProjectHealthResponse(BaseModel):
    """Typed response for per-project health signal."""

    project_id: str
    name: str
    status: str
    conversion_rate: float | None = None
    revenue: float | None = None
    health_score: float = Field(ge=0.0, le=1.0)
    recommendation: str


@router.get("/projects/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(project_id: str) -> ProjectHealthResponse:
    """Return deterministic health score for a project."""
    health = _intelligence.project_health(project_id)
    if health is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectHealthResponse(
        project_id=health.project_id,
        name=health.name,
        status=health.status,
        conversion_rate=health.conversion_rate,
        revenue=health.revenue,
        health_score=health.health_score,
        recommendation=health.recommendation,
    )


@router.get("/ranked-projects", response_model=list[ProjectHealthResponse])
async def get_ranked_projects() -> list[ProjectHealthResponse]:
    """Return all projects ranked by deterministic health score."""
    ranked = _intelligence.ranked_projects()
    return [
        ProjectHealthResponse(
            project_id=item.project_id,
            name=item.name,
            status=item.status,
            conversion_rate=item.conversion_rate,
            revenue=item.revenue,
            health_score=item.health_score,
            recommendation=item.recommendation,
        )
        for item in ranked
    ]
