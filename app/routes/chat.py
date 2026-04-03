"""
chat.py – Routes for conversational interaction with AI-DAN.

Handles incoming chat messages and returns AI-DAN's strategic response.
The route stays thin: validation and delegation only.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.reasoning.models import FounderResponse
from app.reasoning.strategist import Strategist

router = APIRouter()

_strategist = Strategist()


class ChatRequest(BaseModel):
    """Payload for a single chat turn."""

    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


@router.post("/", response_model=FounderResponse)
async def send_message(request: ChatRequest) -> FounderResponse:
    """Accept a user message and return AI-DAN's structured pipeline response.

    Runs the full end-to-end flow: input → reasoning → evaluation →
    planning → commands → response.  Returns the mandatory flat format.
    """
    return _strategist.process_founder_input(
        request.message,
        context=request.context,
    )
