"""
ideas.py – Routes for idea generation and management.

Exposes endpoints for generating, brainstorming, evaluating, and critiquing ideas.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.reasoning.critic import Critic
from app.reasoning.evaluator import Evaluator
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import CritiqueResult, EvaluationResult, Idea

router = APIRouter()

# ---------------------------------------------------------------------------
# Singletons – lightweight, stateless reasoning modules
# ---------------------------------------------------------------------------
_idea_engine = IdeaEngine()
_evaluator = Evaluator()
_critic = Critic()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class IdeaRequest(BaseModel):
    """Payload for submitting a new idea prompt."""

    prompt: str
    context: dict[str, Any] | None = None


class BrainstormRequest(BaseModel):
    """Payload for brainstorming multiple ideas."""

    prompt: str
    count: int = Field(default=5, ge=1, le=5)


class IdeaEvaluateRequest(BaseModel):
    """Payload for evaluating a previously generated idea."""

    idea: Idea


class IdeaCritiqueRequest(BaseModel):
    """Payload for critiquing a previously generated idea."""

    idea: Idea


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=Idea)
async def generate_idea(request: IdeaRequest) -> Idea:
    """Generate a single structured idea from the given prompt."""
    return _idea_engine.generate(request.prompt, request.context)


@router.post("/brainstorm", response_model=list[Idea])
async def brainstorm_ideas(request: BrainstormRequest) -> list[Idea]:
    """Generate multiple candidate ideas for the given prompt."""
    return _idea_engine.brainstorm(request.prompt, request.count)


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_idea(request: IdeaEvaluateRequest) -> EvaluationResult:
    """Score an idea across feasibility, profitability, speed, and competition."""
    return _evaluator.score(request.idea)


@router.post("/critique", response_model=CritiqueResult)
async def critique_idea(request: IdeaCritiqueRequest) -> CritiqueResult:
    """Produce an adversarial critique of the given idea."""
    return _critic.critique(request.idea)
