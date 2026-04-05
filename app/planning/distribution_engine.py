"""
Distribution engine – generates structured distribution plan with rejection.

Output:
- ONE primary channel
- acquisition method
- first 10 users plan
- messaging

If distribution plan is unrealistic → REJECT.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DistributionDecision(str, Enum):
    """Distribution plan outcome."""

    GENERATED = "generated"
    REJECTED = "rejected"


class DistributionOutput(BaseModel):
    """Structured distribution plan output."""

    decision: DistributionDecision
    primary_channel: str = ""
    acquisition_method: str = ""
    first_10_users_plan: str = ""
    messaging: str = ""
    execution_steps: list[str] = Field(default_factory=list)
    estimated_days: int = 14
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# Channel strategies by audience type
# ---------------------------------------------------------------------------
_CHANNEL_STRATEGIES: dict[str, dict[str, Any]] = {
    "developer": {
        "channel": "Product Hunt + Dev Communities",
        "acquisition": "Community-led growth through dev forums, open-source contributions, and technical content",
        "plan": (
            "Launch on Product Hunt, post in r/SideProject and HackerNews. "
            "Write a technical blog post showing the problem and solution. "
            "Engage in relevant Discord/Slack communities."
        ),
        "messaging": "Stop wasting hours on {problem}. {title} automates it in minutes.",
        "steps": [
            "Prepare Product Hunt launch page with demo",
            "Post technical write-up on dev.to and HackerNews",
            "Share in 5 relevant Discord/Slack developer communities",
            "Direct outreach to 10 developers facing this problem",
            "Respond to every comment and piece of feedback",
        ],
        "days": 10,
    },
    "freelancer": {
        "channel": "Twitter/X + Freelancer Communities",
        "acquisition": "Direct outreach and social proof in freelancer circles",
        "plan": (
            "Post daily on Twitter/X about the pain point. "
            "Share in freelancer Slack groups and Reddit communities. "
            "Offer 10 free pilot slots in exchange for testimonials."
        ),
        "messaging": "Freelancers: stop losing money on {problem}. {title} fixes it.",
        "steps": [
            "Create Twitter thread about the problem",
            "Post in r/freelance and r/entrepreneur",
            "Offer free pilot to 10 freelancers in Slack groups",
            "Collect 3 testimonials from pilot users",
            "Create case study from best pilot result",
        ],
        "days": 14,
    },
    "founder": {
        "channel": "LinkedIn + Founder Communities",
        "acquisition": "Warm outreach and founder network referrals",
        "plan": (
            "Personal outreach to 20 founders on LinkedIn. "
            "Post problem/solution narrative on LinkedIn. "
            "Join 3 founder communities and share insights."
        ),
        "messaging": "Fellow founders: {problem} cost me weeks. {title} solves it in hours.",
        "steps": [
            "Send personalized LinkedIn messages to 20 founders",
            "Publish LinkedIn post about the problem journey",
            "Share in Indie Hackers and founder Slack groups",
            "Follow up with interested founders within 24 hours",
            "Book 5 demo calls from responses",
        ],
        "days": 14,
    },
    "business": {
        "channel": "Cold Email + LinkedIn",
        "acquisition": "Targeted B2B outbound with personalized messaging",
        "plan": (
            "Build list of 50 target companies. "
            "Send personalized cold emails with clear ROI proposition. "
            "Follow up on LinkedIn with value-add content."
        ),
        "messaging": "Your team spends 10+ hours/week on {problem}. {title} cuts that to minutes.",
        "steps": [
            "Build prospect list of 50 target companies",
            "Craft personalized email template with ROI hook",
            "Send first batch of 20 emails",
            "Follow up non-responders on LinkedIn after 3 days",
            "Send second batch based on learnings from first",
        ],
        "days": 14,
    },
    "consumer": {
        "channel": "TikTok/Instagram + SEO",
        "acquisition": "Content-led acquisition through short-form video and search",
        "plan": (
            "Create 5 short-form videos showing the problem/solution. "
            "Publish SEO-optimized landing page. "
            "Run micro-influencer collaboration."
        ),
        "messaging": "Tired of {problem}? {title} makes it effortless.",
        "steps": [
            "Create and post 5 TikTok/Reels showing the pain point",
            "Publish SEO landing page with clear CTA",
            "Reach out to 3 micro-influencers for collaboration",
            "Engage with every comment and DM",
            "Iterate content based on highest-performing video",
        ],
        "days": 10,
    },
    "default": {
        "channel": "SEO Landing Page + LinkedIn",
        "acquisition": "Inbound-led growth through search optimization and social proof",
        "plan": (
            "Launch SEO-optimized landing page with clear value prop. "
            "Share on LinkedIn with 5 posts over 2 weeks. "
            "Direct outreach to 20 potential users."
        ),
        "messaging": "Solving {problem} for {target_user}. Try {title} free today.",
        "steps": [
            "Publish SEO-optimized landing page with clear CTA",
            "Write 5 LinkedIn posts about the problem space",
            "Engage in relevant LinkedIn groups",
            "Direct outreach to 20 potential users",
            "Collect feedback and iterate messaging",
        ],
        "days": 14,
    },
}


def _detect_audience_type(target_user: str, idea_text: str) -> str:
    """Detect audience type from target user and idea text."""
    combined = f"{target_user} {idea_text}".lower()

    if any(w in combined for w in ("developer", "engineer", "programmer", "coder")):
        return "developer"
    if any(w in combined for w in ("freelancer", "freelance", "contractor")):
        return "freelancer"
    if any(w in combined for w in ("founder", "startup", "entrepreneur", "solopreneur")):
        return "founder"
    if any(w in combined for w in ("business", "b2b", "enterprise", "company", "team")):
        return "business"
    if any(w in combined for w in ("consumer", "everyone", "people", "individual", "personal")):
        return "consumer"
    return "default"


def generate_distribution(
    *,
    title: str,
    problem: str = "",
    target_user: str = "",
    idea_text: str = "",
    extra: dict[str, Any] | None = None,
) -> DistributionOutput:
    """Generate a focused distribution plan for first-user acquisition.

    Args:
        title: Product/idea title.
        problem: Core problem being solved.
        target_user: Primary audience.
        idea_text: Full idea description for context.
        extra: Optional additional data.

    Returns:
        DistributionOutput with channel strategy or rejection.
    """
    if not title or not title.strip():
        return DistributionOutput(
            decision=DistributionDecision.REJECTED,
            rejection_reason="Missing title — cannot create distribution plan.",
        )
    if not target_user or not target_user.strip():
        return DistributionOutput(
            decision=DistributionDecision.REJECTED,
            rejection_reason="Missing target user — cannot determine distribution channel.",
        )

    audience_type = _detect_audience_type(target_user, idea_text)
    strategy = _CHANNEL_STRATEGIES[audience_type]

    messaging = strategy["messaging"].format(
        title=title,
        problem=problem or "this challenge",
        target_user=target_user,
    )

    return DistributionOutput(
        decision=DistributionDecision.GENERATED,
        primary_channel=strategy["channel"],
        acquisition_method=strategy["acquisition"],
        first_10_users_plan=strategy["plan"],
        messaging=messaging,
        execution_steps=strategy["steps"],
        estimated_days=strategy["days"],
    )
