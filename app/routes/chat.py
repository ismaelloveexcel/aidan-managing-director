"""
chat.py – Routes for conversational interaction with AI-DAN.

Handles incoming chat messages and returns AI-DAN's strategic response.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.reasoning.models import StrategicDirection
from app.reasoning.strategist import Strategist

router = APIRouter()

_strategist = Strategist()


class ChatRequest(BaseModel):
    """Payload for a single chat turn."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response returned for a single chat turn."""

    reply: str
    session_id: str | None = None
    strategy: StrategicDirection | None = None


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Accept a user message and return AI-DAN's strategic analysis."""
    direction = _strategist.analyse({"message": request.message})

    reply = (
        f"Intent detected: {direction.intent.value} "
        f"(confidence {direction.confidence:.0%}). "
        f"Direction: {direction.direction}"
    )

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        strategy=direction,
    )
