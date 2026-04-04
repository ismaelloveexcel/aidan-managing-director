"""
portfolio.py - Routes for persistent portfolio state and lifecycle transitions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_portfolio_repository
from app.portfolio.models import LifecycleState, PortfolioEventRecord, PortfolioProjectRecord
from app.portfolio.state_machine import InvalidStateTransitionError

router = APIRouter()

_portfolio = get_portfolio_repository()


class PortfolioProjectCreateRequest(BaseModel):
    """Request payload for creating a portfolio project."""

    name: str
    description: str
    metadata: dict[str, Any] | None = None
    project_id: str | None = None


class PortfolioTransitionRequest(BaseModel):
    """Request payload for lifecycle transition."""

    new_state: LifecycleState = Field(description="Target lifecycle state.")
    event_type: str | None = None
    payload: dict[str, Any] | None = None


@router.post("/projects", response_model=PortfolioProjectRecord)
async def create_portfolio_project(
    request: PortfolioProjectCreateRequest,
) -> PortfolioProjectRecord:
    """Create a project in the persistent portfolio registry."""
    return _portfolio.create_project(
        name=request.name,
        description=request.description,
        metadata=request.metadata,
        project_id=request.project_id,
    )


@router.get("/projects", response_model=list[PortfolioProjectRecord])
async def list_portfolio_projects() -> list[PortfolioProjectRecord]:
    """List all portfolio projects."""
    return _portfolio.list_projects()


@router.get("/projects/{project_id}", response_model=PortfolioProjectRecord)
async def get_portfolio_project(project_id: str) -> PortfolioProjectRecord:
    """Fetch a single portfolio project."""
    project = _portfolio.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/transition", response_model=PortfolioProjectRecord)
async def transition_portfolio_project(
    project_id: str,
    request: PortfolioTransitionRequest,
) -> PortfolioProjectRecord:
    """Transition project state through enforced lifecycle rules."""
    try:
        project = _portfolio.transition_project_state(
            project_id=project_id,
            new_state=request.new_state,
            event_type=request.event_type,
            payload=request.payload,
        )
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/events", response_model=list[PortfolioEventRecord])
async def list_portfolio_events(project_id: str) -> list[PortfolioEventRecord]:
    """Return audit events for a project."""
    project = _portfolio.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _portfolio.list_events(project_id)
