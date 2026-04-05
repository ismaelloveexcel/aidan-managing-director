"""
distribution.py – Routes for distribution message generation.

Exposes an endpoint that generates platform-optimised share messages
from a project ID or inline product data.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.planning.share_templates import ShareMessageBundle, generate_share_messages

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ShareMessageRequest(BaseModel):
    """Payload for generating distribution share messages."""

    title: str = Field(..., min_length=1, description="Product name or idea title.")
    url: str = Field(..., min_length=1, description="Deployment URL for the product.")
    description: str = Field(
        ...,
        min_length=1,
        description="Short product description (1–2 sentences).",
    )
    target_user: str = Field(
        ...,
        min_length=1,
        description="Primary target audience (e.g. 'freelance developers').",
    )
    cta: str = Field(
        default="Try it free",
        min_length=1,
        description="Call-to-action text.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/share-messages", response_model=ShareMessageBundle)
async def generate_share_messages_endpoint(
    request: ShareMessageRequest,
) -> ShareMessageBundle:
    """Generate ready-to-use distribution messages for multiple platforms.

    Returns platform-optimised copy for Twitter, LinkedIn, WhatsApp,
    email, SMS, Reddit, and Product Hunt — all including the deployment URL.
    """
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail="url must start with http:// or https://",
        )

    return generate_share_messages(
        title=request.title,
        url=request.url,
        description=request.description,
        target_user=request.target_user,
        cta=request.cta,
    )
