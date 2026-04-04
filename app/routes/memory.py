"""
memory.py - Routes for memory and learning signal persistence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_auto_learner, get_memory_store
from app.memory.auto_learner import OUTCOME_TYPES, LearningInsight, OutcomeType
from app.memory.store import LearningSignal

router = APIRouter()

_memory = get_memory_store()
_learner = get_auto_learner()


class MemoryEventRequest(BaseModel):
    """Request payload for recording a raw memory event."""

    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class LearningSignalRequest(BaseModel):
    """Request payload for recording a normalized learning signal."""

    project_id: str
    signal_type: str
    score: float = Field(ge=0.0, le=1.0)
    notes: str = ""


class LearningOutcomeRequest(BaseModel):
    """Request payload for recording a project outcome for auto-learning."""

    project_id: str
    outcome_type: OutcomeType
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
async def record_memory_event(request: MemoryEventRequest) -> dict[str, str]:
    """Record a memory event for later learning introspection."""
    _memory.record_event(
        {
            "event_type": request.event_type,
            "payload": request.payload,
        },
    )
    return {"status": "ok"}


@router.post("/signals")
async def record_learning_signal(request: LearningSignalRequest) -> dict[str, str]:
    """Record a normalized learning signal for a project."""
    _memory.record_signal(
        LearningSignal(
            project_id=request.project_id,
            signal_type=request.signal_type,
            score=request.score,
            notes=request.notes,
        ),
    )
    return {"status": "ok"}


@router.post("/outcomes")
async def record_learning_outcome(request: LearningOutcomeRequest) -> dict[str, str]:
    """Record a project outcome for the auto-learning system."""
    _learner.record_outcome(
        project_id=request.project_id,
        outcome_type=request.outcome_type,
        score=request.score,
        metadata=request.metadata,
    )
    return {"status": "ok"}


@router.get("/learning/insight", response_model=LearningInsight)
async def get_learning_insight() -> LearningInsight:
    """Return aggregated auto-learning insight and recommended weight adjustments."""
    return _learner.generate_insight()


@router.get("/events")
async def list_memory_events(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent memory events."""
    return _memory.recent_events(limit=limit)


@router.get("/projects/{project_id}/learning")
async def get_project_learning(project_id: str) -> dict[str, Any]:
    """Return deterministic project-learning summary."""
    return _memory.summarize_project_learning(project_id)
