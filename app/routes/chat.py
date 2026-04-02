"""
chat.py – Routes for conversational interaction with AI-DAN.

Handles incoming chat messages and returns AI-DAN's strategic response.
The route stays thin: validation and delegation only.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.reasoning.models import (
    CommandOutput,
    FounderResponse,
    Risk,
    StrategicDirection,
)
from app.reasoning.strategist import Strategist

router = APIRouter()

_strategist = Strategist()


class ChatRequest(BaseModel):
    """Payload for a single chat turn."""

    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Response returned for a single chat turn."""

    reply: str
    session_id: str | None = None
    strategy: StrategicDirection | None = None
    founder_response: FounderResponse | None = None


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """Accept a user message and return AI-DAN's strategic analysis.

    Delegates all reasoning to the strategist's founder-to-command flow
    and returns the full structured response alongside a human-readable
    reply.
    """
    founder = _strategist.process_founder_input(
        request.message,
        context=request.context,
    )

    reply = (
        f"Intent detected: {founder.strategy.intent.value} "
        f"(confidence {founder.strategy.confidence:.0%}). "
        f"Decision: {founder.decision}"
    )

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        strategy=founder.strategy,
        founder_response=founder,
    )
