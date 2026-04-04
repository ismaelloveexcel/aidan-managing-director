"""
control.py – API surface for command-center and observability controls.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.command_center.models import (
    CommandCenterEntry,
    CommandCenterState,
    CommandStatusUpdateRequest,
)
from app.core.dependencies import get_command_center_service, get_control_plane
from app.observability.control import CircuitState

router = APIRouter()

_control = get_control_plane()
_command_center = get_command_center_service()


class CircuitToggleRequest(BaseModel):
    """Request payload for toggling a circuit breaker."""

    circuit: str = Field(description="Circuit name")
    state: CircuitState = Field(description="Desired circuit state")
    reason: str = Field(default="", description="Operator rationale")


@router.get("/state", response_model=CommandCenterState)
async def get_command_center_state() -> CommandCenterState:
    """Return a compact command-center state snapshot."""
    return _command_center.overview()


@router.post("/circuit", response_model=dict[str, str])
async def toggle_circuit(payload: CircuitToggleRequest) -> dict[str, str]:
    """Toggle a named circuit breaker state."""
    _control.set_circuit(payload.circuit, payload.state, payload.reason)
    return {
        "circuit": payload.circuit,
        "state": payload.state.value,
        "reason": payload.reason,
    }


@router.patch("/commands/status", response_model=CommandCenterEntry)
async def update_command_status(payload: CommandStatusUpdateRequest) -> CommandCenterEntry:
    """Update command status from command center controls."""
    entry = _command_center.update_status(payload)
    if entry is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return entry
