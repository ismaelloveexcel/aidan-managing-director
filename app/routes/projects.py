"""
projects.py – Routes for project portfolio management.

Handles listing, creating, and updating projects tracked by AI-DAN.
Delegates persistence to the registry client.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.integrations.registry_client import RegistryClient
from app.reasoning.models import ProjectRecord, ProjectStatus

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared registry client – lightweight, reused across requests
# ---------------------------------------------------------------------------
_settings = get_settings()
_registry = RegistryClient(
    registry_url=_settings.registry_url,
    api_key=_settings.registry_api_key,
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    """Payload for creating a new project."""

    name: str
    description: str
    repository_url: str | None = None


class ProjectStatusUpdateRequest(BaseModel):
    """Payload for updating a project's status."""

    status: ProjectStatus


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=ProjectRecord)
async def create_project(request: ProjectCreateRequest) -> ProjectRecord:
    """Create a new project entry in the portfolio via the registry."""
    metadata: dict[str, str] = {}
    if request.repository_url:
        metadata["repository_url"] = request.repository_url

    record = _registry.create_project_record(
        name=request.name,
        description=request.description,
        metadata=metadata if metadata else None,
    )
    return ProjectRecord(**record)


@router.get("/", response_model=list[ProjectRecord])
async def list_projects() -> list[ProjectRecord]:
    """Return all projects in the portfolio."""
    records = _registry.list_projects()
    return [ProjectRecord(**r) for r in records]


@router.get("/{project_id}", response_model=ProjectRecord)
async def get_project(project_id: str) -> ProjectRecord:
    """Return details for a specific project by ID."""
    record = _registry.get_project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRecord(**record)


@router.patch("/{project_id}/status", response_model=ProjectRecord)
async def update_project_status(
    project_id: str,
    request: ProjectStatusUpdateRequest,
) -> ProjectRecord:
    """Update the lifecycle status of an existing project."""
    existing = _registry.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Project not found")

    record = _registry.update_project_status(
        project_id=project_id,
        status=request.status.value,
    )
    return ProjectRecord(**record)
