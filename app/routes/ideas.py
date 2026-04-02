"""
ideas.py – Routes for idea generation and management.

Exposes endpoints for creating, listing, and evaluating ideas.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class IdeaRequest(BaseModel):
    """Payload for submitting a new idea prompt."""

    prompt: str
    context: dict | None = None


class IdeaResponse(BaseModel):
    """Structured representation of a generated idea."""

    idea_id: str
    title: str
    summary: str


@router.post("/generate", response_model=IdeaResponse)
async def generate_idea(request: IdeaRequest) -> IdeaResponse:
    """
    Generate a new idea based on the given prompt and optional context.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError


@router.get("/", response_model=list[IdeaResponse])
async def list_ideas() -> list[IdeaResponse]:
    """
    Return all stored ideas.

    Business logic to be implemented in a future iteration.
    """
    raise NotImplementedError
