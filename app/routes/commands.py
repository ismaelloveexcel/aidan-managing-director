"""
commands.py – Routes for dispatching commands to the GitHub Factory.

Handles compiling, validating, and routing structured commands produced
by the planning layer to downstream systems.  Commands are persisted
through the registry client.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.telemetry import emit_event
from app.core.dependencies import get_registry_client
from app.reasoning.models import CommandRecord

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared registry client – single instance across all route modules
# ---------------------------------------------------------------------------
_registry = get_registry_client()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CommandRequest(BaseModel):
    """Payload for dispatching a new command."""

    command_type: str
    parameters: dict[str, Any]
    project_id: str | None = None


class CommandResponse(BaseModel):
    """Status response after a command is dispatched."""

    command_id: str
    status: str
    message: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/dispatch", response_model=CommandRecord)
async def dispatch_command(request: CommandRequest) -> CommandRecord:
    """Compile and dispatch a command, persisting it via the registry."""
    record = _registry.create_command_record(
        command_type=request.command_type,
        parameters=request.parameters,
        project_id=request.project_id,
    )
    emit_event(
        "command_dispatched",
        {
            "command_id": record["record_id"],
            "command_type": request.command_type,
            "project_id": request.project_id,
        },
    )
    return CommandRecord(**record)


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command_status(command_id: str) -> CommandResponse:
    """Return the current status of a previously dispatched command."""
    record = _registry.get_command_record(command_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return CommandResponse(
        command_id=record["record_id"],
        status=record["status"],
        message=record.get("message"),
    )
