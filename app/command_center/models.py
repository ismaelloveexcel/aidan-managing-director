"""
Typed models for command center route surfaces.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommandCenterEntry(BaseModel):
    """Single command item for operator queue views."""

    command_id: str
    command_type: str
    status: str
    project_id: str | None = None
    created_at: str
    updated_at: str | None = None


class CommandCenterSummary(BaseModel):
    """Summary of command queue state plus latest entries."""

    total_commands: int = Field(ge=0)
    pending: int = Field(ge=0)
    running: int = Field(ge=0)
    failed: int = Field(ge=0)
    latest: list[CommandCenterEntry] = Field(default_factory=list)


class CommandStatusUpdateRequest(BaseModel):
    """Request payload for operator command status updates."""

    command_id: str
    status: str
    message: str | None = None


class CommandCenterState(BaseModel):
    """Top-level state snapshot for command-center dashboard surfaces."""

    approvals_pending: int = Field(ge=0)
    projects_active: int = Field(ge=0)
    commands_pending: int = Field(ge=0)
    commands_running: int = Field(ge=0)
    commands_failed: int = Field(ge=0)
    factory_runs_running: int = Field(ge=0)
    factory_runs_failed: int = Field(ge=0)

