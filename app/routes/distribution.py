"""
distribution.py – Routes for distribution message generation.

Exposes endpoints that generate platform-optimised share messages
from a project ID or inline product data, with region-aware content.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from app.core.dependencies import get_marketing_engine
from app.integrations.marketing_engine import REGION_PLATFORMS, MarketingEngine
from app.planning.share_templates import ShareMessageBundle, generate_share_messages

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ShareMessageRequest(BaseModel):
    """Payload for generating distribution share messages (legacy)."""

    title: str = Field(..., min_length=1, description="Product name or idea title.")
    url: HttpUrl = Field(..., description="Deployment URL for the product.")
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


class GenerateCampaignRequest(BaseModel):
    """Payload for generating a full region-aware marketing campaign."""

    title: str = Field(..., min_length=1, description="Product name or idea title.")
    url: HttpUrl = Field(..., description="Deployment URL for the product.")
    description: str = Field(
        ...,
        min_length=1,
        description="Short product description (1–2 sentences).",
    )
    target_user: str = Field(
        default="",
        description="Primary target audience.",
    )
    cta: str = Field(
        default="Try it free",
        description="Call-to-action text.",
    )
    target_region: str = Field(
        default="global",
        description="Target region key (e.g. 'mena', 'africa', 'global').",
    )
    platforms: list[str] | None = Field(
        default=None,
        description="Specific platforms to generate for. If None, uses region defaults.",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional project ID for reference.",
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
    return generate_share_messages(
        title=request.title,
        url=str(request.url),
        description=request.description,
        target_user=request.target_user,
        cta=request.cta,
    )


@router.post("/generate")
async def generate_campaign_endpoint(
    request: GenerateCampaignRequest,
    engine: Annotated[MarketingEngine, Depends(get_marketing_engine)],
) -> dict:
    """Generate a full region-aware marketing campaign.

    Returns platform-specific content for all platforms relevant to the
    target region — TikTok, Instagram, WhatsApp, Facebook, Reddit, etc.
    Single AI call generates all platforms to keep costs minimal.
    """
    return engine.generate_campaign(
        title=request.title,
        description=request.description,
        target_user=request.target_user,
        url=str(request.url),
        cta=request.cta,
        region=request.target_region,
        platforms=request.platforms,
    )


@router.get("/regions")
async def list_regions() -> dict:
    """Return the supported regions and their platform priorities.

    Used by the frontend to populate the region selector dropdown.
    """
    return {
        "regions": {
            key: {
                "label": val["label"],
                "emoji": val.get("emoji", "🌍"),
                "primary": val["primary"],
                "notes": val["notes"],
            }
            for key, val in REGION_PLATFORMS.items()
        }
    }
