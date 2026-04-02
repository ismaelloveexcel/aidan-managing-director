"""
commands.py – Routes for dispatching commands to the GitHub Factory.

Handles compiling, validating, and routing structured commands produced
by the planning layer to downstream systems.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CommandRequest(BaseModel):
    """Payload for dispatching a new command."""

    command_type: str
    parameters: dict
    project_id: str | None = None


class CommandResponse(BaseModel):
    """Status response after a command is dispatched."""

    command_id: str
    status: str
    message: str | None = None


@router.post("/dispatch", response_model=CommandResponse)
async def dispatch_command(request: CommandRequest) -> CommandResponse:
    """
    Compile and dispatch a command to the appropriate downstream system.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command_status(command_id: str) -> CommandResponse:
    """
    Return the current status of a previously dispatched command.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError
