"""
competitor_analysis.py – Reusable competitor analysis skill.

Uses GuardianAgent.assess_competition() for the deterministic baseline and
enriches it with category-specific competitor names and positioning based on
keyword detection.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents.guardian import GuardianAgent


class CompetitorAnalysis(BaseModel):
    """Structured output from competitor analysis."""

    competitor_count: int
    top_competitors: list[dict[str, str]] = Field(default_factory=list)
    market_gap: str
    differentiation_score: float = Field(ge=0.0, le=1.0)
    recommended_positioning: str


# ---------------------------------------------------------------------------
# Category-specific competitor knowledge
# ---------------------------------------------------------------------------
_CATEGORY_COMPETITORS: dict[str, list[dict[str, str]]] = {
    "ai_recruiting": [
        {"name": "HireEZ", "strength": "AI sourcing", "weakness": "Expensive for SMBs"},
        {"name": "Beamery", "strength": "Talent CRM", "weakness": "Complex onboarding"},
        {"name": "Paradox (Olivia)", "strength": "Conversational AI", "weakness": "Limited customisation"},
    ],
    "ai_assistant": [
        {"name": "ChatGPT (OpenAI)", "strength": "Broad capability", "weakness": "Generic, not vertical-specific"},
        {"name": "Microsoft Copilot", "strength": "Enterprise integration", "weakness": "Requires M365 stack"},
        {"name": "Jasper AI", "strength": "Marketing content", "weakness": "Narrow use-case"},
    ],
    "analytics_dashboard": [
        {"name": "Tableau", "strength": "Visual depth", "weakness": "High cost and complexity"},
        {"name": "Looker", "strength": "GCP integration", "weakness": "Developer-heavy setup"},
        {"name": "Metabase", "strength": "Open source", "weakness": "Limited AI features"},
    ],
    "marketplace": [
        {"name": "Fiverr", "strength": "Brand recognition", "weakness": "Race to bottom on price"},
        {"name": "Upwork", "strength": "Enterprise contracts", "weakness": "High fees"},
        {"name": "Toptal", "strength": "Vetting quality", "weakness": "Very expensive"},
    ],
    "education": [
        {"name": "Coursera", "strength": "University partnerships", "weakness": "Passive learning"},
        {"name": "Udemy", "strength": "Huge catalogue", "weakness": "Quality inconsistency"},
        {"name": "Skillshare", "strength": "Creative niche", "weakness": "Not for professional certs"},
    ],
    "workflow_automation": [
        {"name": "Zapier", "strength": "Huge app ecosystem", "weakness": "Expensive at scale"},
        {"name": "Make (Integromat)", "strength": "Visual builder", "weakness": "Learning curve"},
        {"name": "n8n", "strength": "Self-hosted option", "weakness": "Requires technical knowledge"},
    ],
}

_DEFAULT_COMPETITORS: list[dict[str, str]] = [
    {"name": "Established SaaS player", "strength": "Market trust", "weakness": "Slow innovation"},
    {"name": "Open-source alternative", "strength": "Free tier", "weakness": "No support"},
    {"name": "Niche specialist", "strength": "Deep feature set", "weakness": "Narrow audience"},
]

_MARKET_GAP_TEMPLATES: dict[str, str] = {
    "ai_recruiting": "Affordable AI recruiting tools tailored for SMBs.",
    "ai_assistant": "Vertical-specific AI assistant with deep domain knowledge.",
    "analytics_dashboard": "Self-serve analytics requiring no BI expertise.",
    "marketplace": "Trust-first marketplace with verified quality tiers.",
    "education": "Outcome-focused learning with real-world project integration.",
    "workflow_automation": "No-code automation for non-technical operators.",
}

_DEFAULT_MARKET_GAP = "Focused solution targeting an underserved sub-segment of the market."

_POSITIONING_TEMPLATES: dict[str, str] = {
    "ai_recruiting": "Position as the affordable, founder-friendly recruiting AI for growing startups.",
    "ai_assistant": "Position as the specialist AI for {vertical}, not a generic chatbot.",
    "analytics_dashboard": "Position as the analytics layer for operators, not data scientists.",
    "marketplace": "Position around trust and quality guarantees to justify premium pricing.",
    "education": "Position around measurable outcomes: skills, certs, and job-ready projects.",
    "workflow_automation": "Position as the automation layer for solo operators with zero code.",
}

_DEFAULT_POSITIONING = (
    "Differentiate on speed, simplicity, and laser focus on one vertical."
)

_GUARDIAN = GuardianAgent()


def analyze_competitors(
    idea_text: str,
    target_user: str,
    competition_level: str,
) -> CompetitorAnalysis:
    """Analyse the competitive landscape for a given idea.

    Uses :meth:`~app.agents.guardian.GuardianAgent.assess_competition` for the
    baseline competitor count and saturation assessment, then enriches the
    result with category-specific competitor names and positioning.

    ``competition_level`` adjusts the final competitor count upward when the
    caller explicitly signals high competition (e.g. "high", "very high"), or
    downward for "low"/"none" markets, on top of the heuristic baseline.

    Args:
        idea_text: Full description of the idea.
        target_user: Description of the target user.
        competition_level: Explicit competition level hint (low/medium/high).

    Returns:
        CompetitorAnalysis with competitor_count, top_competitors, market_gap,
        differentiation_score, and recommended_positioning.
    """
    build_brief: dict[str, Any] = {
        "title": idea_text[:80],
        "problem": idea_text,
        "solution": idea_text,
        "target_user": target_user,
    }
    heuristic = _GUARDIAN.assess_competition(build_brief=build_brief)

    # Adjust competitor_count based on explicit competition_level hint
    _level = competition_level.lower().strip()
    if _level in {"high", "very high", "extreme"}:
        adjusted_count = max(heuristic.competitor_count, 15)
    elif _level in {"low", "none", "very low"}:
        adjusted_count = min(heuristic.competitor_count, 5)
    else:
        adjusted_count = heuristic.competitor_count

    # Pick the first matched category to enrich with named competitors
    primary_category = heuristic.matched_categories[0] if heuristic.matched_categories else None

    top_competitors = (
        _CATEGORY_COMPETITORS.get(primary_category, _DEFAULT_COMPETITORS)
        if primary_category
        else _DEFAULT_COMPETITORS
    )

    market_gap = (
        _MARKET_GAP_TEMPLATES.get(primary_category, _DEFAULT_MARKET_GAP)
        if primary_category
        else _DEFAULT_MARKET_GAP
    )

    positioning_template = (
        _POSITIONING_TEMPLATES.get(primary_category, _DEFAULT_POSITIONING)
        if primary_category
        else _DEFAULT_POSITIONING
    )
    recommended_positioning = positioning_template.replace("{vertical}", primary_category or "your market")

    # Map similarity_score → differentiation_score (inverse)
    differentiation_score = round(1.0 - heuristic.similarity_score, 2)

    return CompetitorAnalysis(
        competitor_count=adjusted_count,
        top_competitors=list(top_competitors),
        market_gap=market_gap,
        differentiation_score=differentiation_score,
        recommended_positioning=recommended_positioning,
    )
