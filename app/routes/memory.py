"""
memory.py - Routes for memory and learning signal persistence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_memory_store
from app.memory.store import LearningSignal

router = APIRouter()

_memory = get_memory_store()


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


@router.get("/events")
async def list_memory_events(limit: int = 25) -> list[dict[str, Any]]:
    """Return recent memory events."""
    return _memory.recent_events(limit=limit)


@router.get("/projects/{project_id}/learning")
async def get_project_learning(project_id: str) -> dict[str, Any]:
    """Return deterministic project-learning summary."""
    return _memory.summarize_project_learning(project_id)
