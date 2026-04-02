"""
projects.py – Routes for project portfolio management.

Handles listing, creating, and updating projects tracked by AI-DAN.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ProjectRequest(BaseModel):
    """Payload for creating or updating a project."""

    name: str
    description: str
    repository_url: str | None = None


class ProjectResponse(BaseModel):
    """Structured representation of a project."""

    project_id: str
    name: str
    description: str
    status: str


@router.post("/", response_model=ProjectResponse)
async def create_project(request: ProjectRequest) -> ProjectResponse:
    """
    Create a new project entry in the portfolio.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError


@router.get("/", response_model=list[ProjectResponse])
async def list_projects() -> list[ProjectResponse]:
    """
    Return all projects in the portfolio.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    """
    Return details for a specific project by ID.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError
