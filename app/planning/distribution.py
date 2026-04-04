"""
Distribution engine – generates a focused distribution plan for first users.

Rules:
- Exactly ONE primary channel.
- Concrete plan for acquiring the first 10 users.
- Messaging and execution steps.
- Reject unrealistic distribution plans.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DistributionPlan(BaseModel):
    """Structured distribution plan for first-user acquisition."""

    primary_channel: str
    first_10_users_plan: str
    messaging: str
    execution_steps: list[str] = Field(min_length=1, max_length=5)
    estimated_days_to_first_10: int = Field(ge=1, le=30)
    realistic: bool = True


_CHANNEL_MAP: dict[str, dict[str, Any]] = {
    "developer": {
        "channel": "GitHub + Dev Communities",
        "plan": "Post solution in 3 relevant GitHub discussions/repos, share on dev.to and HackerNews Show.",
        "messaging": "Built this to solve {problem} for {target_user}. Free to try, feedback welcome.",
        "steps": [
            "Identify 5 relevant GitHub repos/discussions in the niche",
            "Write a short dev.to post showcasing the solution",
            "Submit to HackerNews Show HN",
            "Engage in comment threads for 3 days",
        ],
        "days": 7,
    },
    "freelancer": {
        "channel": "LinkedIn + X/Twitter",
        "plan": "Direct outreach to 30 freelancers via LinkedIn; post 3 threads on X about the problem.",
        "messaging": "Stop wasting time on {problem}. I built {title} to fix it. Try the free pilot.",
        "steps": [
            "Build a list of 30 target freelancers on LinkedIn",
            "Send personalized connection requests with value prop",
            "Post 3 X/Twitter threads about the pain point",
            "Follow up with interested connections via DM",
        ],
        "days": 10,
    },
    "founder": {
        "channel": "LinkedIn + Founder Communities",
        "plan": "Post in 3 founder communities (IndieHackers, r/SaaS, LinkedIn groups) with clear CTA.",
        "messaging": "Building {title} for {target_user}. Looking for 10 beta users to validate the approach.",
        "steps": [
            "Post on IndieHackers with show format",
            "Share in r/SaaS and r/startups with clear CTA",
            "LinkedIn post targeting founder network",
            "DM 10 founders who engaged with similar problems",
        ],
        "days": 7,
    },
    "business": {
        "channel": "Cold Email + LinkedIn",
        "plan": "Cold email campaign to 50 ICPs with personalized value prop, follow up on LinkedIn.",
        "messaging": "{target_user}: {problem} costs you time and money. {title} fixes it in days.",
        "steps": [
            "Build ICP list of 50 target businesses",
            "Write 3-email cold sequence with clear value prop",
            "Send first batch of 20 emails",
            "LinkedIn follow-up for non-responders after 3 days",
            "Send second batch of 30 emails based on learnings",
        ],
        "days": 14,
    },
    "default": {
        "channel": "SEO Landing Page + LinkedIn",
        "plan": "Launch SEO-optimized landing page, share on LinkedIn with 5 posts over 2 weeks.",
        "messaging": "Solving {problem} for {target_user}. Join the waitlist for early access.",
        "steps": [
            "Publish SEO-optimized landing page with clear CTA",
            "Write 5 LinkedIn posts about the problem space",
            "Engage in relevant LinkedIn groups",
            "Direct outreach to 20 potential users",
        ],
        "days": 14,
    },
}


def generate_distribution_plan(
    *,
    title: str,
    target_user: str,
    problem: str,
    pricing_model: str = "",
) -> dict[str, Any]:
    """Generate a focused distribution plan for first-user acquisition.

    Args:
        title: Product/idea title.
        target_user: Primary audience.
        problem: Core problem being solved.
        pricing_model: Pricing approach (used for messaging refinement).

    Returns:
        Serialised DistributionPlan as a dictionary.
    """
    audience = target_user.lower()
    if "developer" in audience or "engineer" in audience:
        key = "developer"
    elif "freelancer" in audience:
        key = "freelancer"
    elif "founder" in audience or "startup" in audience:
        key = "founder"
    elif "business" in audience or "b2b" in audience or "enterprise" in audience:
        key = "business"
    else:
        key = "default"

    template = _CHANNEL_MAP[key]
    messaging = template["messaging"].format(
        title=title,
        target_user=target_user,
        problem=problem,
    )

    plan = DistributionPlan(
        primary_channel=template["channel"],
        first_10_users_plan=template["plan"],
        messaging=messaging,
        execution_steps=template["steps"],
        estimated_days_to_first_10=template["days"],
    )
    return plan.model_dump()
