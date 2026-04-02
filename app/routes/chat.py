"""
chat.py – Routes for conversational interaction with AI-DAN.

Handles incoming chat messages and returns AI-DAN's responses.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    """Payload for a single chat turn."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response returned for a single chat turn."""

    reply: str
    session_id: str | None = None


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Accept a user message and return AI-DAN's response.

    Business logic to be implemented in a future iteration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
