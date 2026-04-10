"""
chat.py – Routes for conversational interaction with AI-DAN.

Two modes:
- POST /chat/  – full pipeline flow via Strategist (structured FounderResponse)
- POST /chat/talk  – lightweight conversational endpoint with AI-DAN personality
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_ai_provider
from app.integrations.ai_provider import AIProvider
from app.reasoning.models import FounderResponse
from app.reasoning.strategist import Strategist

router = APIRouter()

_strategist = Strategist()


class ChatRequest(BaseModel):
    """Payload for a single chat turn (pipeline mode)."""

    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class TalkRequest(BaseModel):
    """Payload for a conversational AI-DAN message."""

    message: str
    history: list[dict[str, str]] | None = None  # [{"role": "user|assistant", "content": "..."}]
    context: dict[str, Any] | None = None


class TalkResponse(BaseModel):
    """Response from the AI-DAN conversational endpoint."""

    reply: str
    model: str = "stub"


@router.post("/", response_model=FounderResponse)
async def send_message(request: ChatRequest) -> FounderResponse:
    """Full pipeline flow: input \u2192 reasoning \u2192 evaluation \u2192 planning \u2192 response."""
    return _strategist.process_founder_input(
        request.message,
        context=request.context,
    )


@router.post("/talk", response_model=TalkResponse)
async def talk(
    request: TalkRequest,
    ai: AIProvider = Depends(get_ai_provider),
) -> TalkResponse:
    """Conversational AI-DAN with personality.

    Uses the best available AI model (Claude > OpenAI > Groq > Deepseek > Grok)
    with AI-DAN's brutally honest venture-advisor personality.
    Returns a plain text reply and the model name used.
    """
    reply, model = ai.aidan_chat(
        message=request.message,
        history=request.history,
        context=request.context,
    )
    return TalkResponse(reply=reply, model=model)
