"""
Offer engine – generates STRUCTURED offer output for approved ideas.

Required output:
- problem
- target_customer
- core_offer
- value
- pricing (MANDATORY)
- delivery
- CTA

If any critical field is unclear → REJECT.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OfferDecision(str, Enum):
    """Offer generation outcome."""

    GENERATED = "generated"
    REJECTED = "rejected"


class OfferOutput(BaseModel):
    """Structured offer for a validated idea."""

    decision: OfferDecision
    problem: str = ""
    target_customer: str = ""
    core_offer: str = ""
    value_proposition: str = ""
    pricing: str = ""
    pricing_model: str = ""
    delivery_method: str = ""
    cta: str = ""
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# Pricing templates based on monetization model
# ---------------------------------------------------------------------------
_PRICING_MAP: dict[str, dict[str, str]] = {
    "subscription": {
        "pricing": "$19/mo starter, $49/mo pro, $99/mo business",
        "model": "Monthly SaaS subscription",
        "delivery": "Cloud-hosted web application with instant access",
    },
    "saas": {
        "pricing": "$29/mo starter, $79/mo pro, $199/mo enterprise",
        "model": "Tiered SaaS subscription",
        "delivery": "Cloud-hosted platform with API access",
    },
    "freemium": {
        "pricing": "Free tier (limited), $19/mo pro, $49/mo team",
        "model": "Freemium with paid upgrades",
        "delivery": "Web app with instant signup, upgrade in-app",
    },
    "marketplace": {
        "pricing": "10-15% transaction fee per sale",
        "model": "Marketplace commission",
        "delivery": "Two-sided platform connecting buyers and sellers",
    },
    "one-time": {
        "pricing": "$49 one-time purchase, $99 premium bundle",
        "model": "One-time purchase",
        "delivery": "Instant digital download or access",
    },
    "api": {
        "pricing": "Free tier (100 calls/day), $29/mo (10K calls), $99/mo (100K calls)",
        "model": "Usage-based API pricing",
        "delivery": "REST API with key-based authentication",
    },
    "ads": {
        "pricing": "Free for users, CPM/CPC revenue from advertisers",
        "model": "Advertising revenue",
        "delivery": "Free web/mobile app with ad placements",
    },
    "affiliate": {
        "pricing": "Free for users, 5-20% affiliate commission on referrals",
        "model": "Affiliate/referral revenue",
        "delivery": "Content platform with embedded affiliate links",
    },
    "default": {
        "pricing": "$19/mo basic, $49/mo professional",
        "model": "Subscription",
        "delivery": "Cloud-hosted web application",
    },
}


def _detect_monetization_type(monetization_model: str, idea_text: str) -> str:
    """Detect the most appropriate pricing template key."""
    combined = f"{monetization_model} {idea_text}".lower()

    for key in _PRICING_MAP:
        if key == "default":
            continue
        if key in combined:
            return key

    # Fallback keyword detection
    if any(w in combined for w in ("monthly", "recurring", "subscribe")):
        return "subscription"
    if any(w in combined for w in ("free tier", "free plan", "upgrade")):
        return "freemium"
    if any(w in combined for w in ("one time", "one-time", "lifetime")):
        return "one-time"

    return "default"


def _generate_cta(title: str, target_customer: str) -> str:
    """Generate a clear call-to-action."""
    return f"Start your free trial of {title} today — built for {target_customer}."


def _generate_value_proposition(problem: str, title: str) -> str:
    """Generate value proposition from problem and title."""
    if problem:
        return f"{title} eliminates {problem.rstrip('.')} — saving you time and money."
    return f"{title} — the fastest path to solving your core challenge."


def generate_offer(
    *,
    title: str,
    problem: str = "",
    target_user: str = "",
    monetization_model: str = "",
    solution: str = "",
    idea_text: str = "",
    extra: dict[str, Any] | None = None,
) -> OfferOutput:
    """Generate a structured offer for a validated idea.

    Args:
        title: Idea/product title.
        problem: Core problem being solved.
        target_user: Target customer description.
        monetization_model: Proposed revenue model.
        solution: Solution description.
        idea_text: Full idea text for context.
        extra: Optional extra data.

    Returns:
        OfferOutput with all fields populated or rejection reason.
    """
    # Validate minimum required fields
    if not title or not title.strip():
        return OfferOutput(
            decision=OfferDecision.REJECTED,
            rejection_reason="Missing title — cannot generate offer without a product name.",
        )
    if not problem or not problem.strip():
        return OfferOutput(
            decision=OfferDecision.REJECTED,
            rejection_reason="Missing problem statement — offer requires a clear problem.",
        )
    if not target_user or not target_user.strip():
        return OfferOutput(
            decision=OfferDecision.REJECTED,
            rejection_reason="Missing target customer — offer requires a defined audience.",
        )

    # Detect pricing model
    pricing_key = _detect_monetization_type(monetization_model, idea_text)
    pricing_info = _PRICING_MAP[pricing_key]

    # Build core offer
    core_offer = solution.strip() if solution.strip() else (
        f"An automated solution that solves {problem.rstrip('.')} "
        f"for {target_user}."
    )

    return OfferOutput(
        decision=OfferDecision.GENERATED,
        problem=problem.strip(),
        target_customer=target_user.strip(),
        core_offer=core_offer,
        value_proposition=_generate_value_proposition(problem, title),
        pricing=pricing_info["pricing"],
        pricing_model=pricing_info["model"],
        delivery_method=pricing_info["delivery"],
        cta=_generate_cta(title, target_user),
    )
