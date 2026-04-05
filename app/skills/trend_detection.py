"""
trend_detection.py – Reusable trend detection skill.

Keyword-based trend detection across technology and business categories.
Maps idea keywords to trend categories with growth signals and timing
assessments.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrendReport(BaseModel):
    """Structured output from trend detection."""

    trending_up: list[str] = Field(default_factory=list)
    trending_down: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0)
    timing_assessment: Literal["EARLY", "OPTIMAL", "LATE"]
    recommendation: str


# ---------------------------------------------------------------------------
# Trend category definitions
# ---------------------------------------------------------------------------

# Keywords → trend category name
_TRENDING_UP_MAP: dict[str, tuple[str, ...]] = {
    "AI / LLM tooling": (
        "ai", "llm", "gpt", "copilot", "agent", "generative", "transformer",
        "chatbot", "neural", "embedding", "rag",
    ),
    "AI automation": (
        "automation", "workflow", "automate", "agentic", "orchestration",
    ),
    "Vertical SaaS": (
        "vertical", "niche", "specific", "industry", "sector",
    ),
    "No-code / Low-code": (
        "no-code", "nocode", "low-code", "visual builder", "drag and drop",
    ),
    "API-first products": (
        "api", "sdk", "developer", "integration", "webhook",
    ),
    "Remote work tooling": (
        "remote", "async", "distributed", "hybrid", "work from home",
    ),
    "FinTech / Payments": (
        "payment", "fintech", "invoice", "billing", "wallet", "stripe",
    ),
    "HealthTech": (
        "health", "wellness", "telemedicine", "fitness", "mental health",
    ),
    "Creator economy tools": (
        "creator", "content creator", "newsletter", "podcast", "streamer",
    ),
    "Cybersecurity": (
        "security", "cyber", "privacy", "compliance", "zero trust",
    ),
}

_TRENDING_DOWN_MAP: dict[str, tuple[str, ...]] = {
    "Traditional desktop software": (
        "desktop app", "windows app", "install", "executable", ".exe",
    ),
    "Generic social networks": (
        "social network", "social platform", "another facebook", "another twitter",
    ),
    "Manual / spreadsheet workflows": (
        "spreadsheet", "excel workflow", "manual entry", "csv import",
    ),
    "Basic CRUD apps": (
        "crud", "todo app", "note taking", "simple notes",
    ),
    "Monolithic ERP": (
        "erp implementation", "on-premise", "legacy system", "mainframe",
    ),
    "Ad-supported consumer apps": (
        "ad-supported", "free with ads", "advertising model", "banner ads",
    ),
}

# Weights used in relevance_score calculation.
# Each matching up-trend category adds 0.12 to raw relevance (max ~1.0 at ~8 matches).
# Each matching down-trend category subtracts 0.08, penalising declining-market ideas.
# These values were chosen so that 2-3 strong up-trend matches yield a meaningful
# positive score (~0.25-0.35) without a single match saturating the scale.
_UP_WEIGHT = 0.12
_DOWN_WEIGHT = 0.08
_MAX_RELEVANCE = 1.0


def _token_set(text: str) -> set[str]:
    """Return lowercase word tokens from text."""
    return {w.strip(".,;:!?()[]{}\"'") for w in text.lower().split()}


def detect_trends(
    idea_text: str,
    target_user: str = "",
) -> TrendReport:
    """Detect market trends relevant to an idea using keyword analysis.

    Maps idea keywords to categorised trend signals.  Categories with matching
    keywords are included in ``trending_up`` or ``trending_down`` lists.

    ``relevance_score`` reflects how strongly the idea aligns with growth
    trends (0.0 = no alignment, 1.0 = maximum alignment).

    ``timing_assessment`` is derived from the balance of up vs down signals:
    - EARLY: strong up signals, no down signals — market still forming
    - OPTIMAL: up signals outweigh down — good timing
    - LATE: down signals equal or exceed up — market declining or saturated

    Args:
        idea_text: Full description of the idea.
        target_user: Optional target user description for additional context.

    Returns:
        TrendReport with trending_up, trending_down, relevance_score,
        timing_assessment, and recommendation.
    """
    combined = f"{idea_text} {target_user}".lower()
    tokens = _token_set(combined)

    matched_up: list[str] = []
    matched_down: list[str] = []

    for category, keywords in _TRENDING_UP_MAP.items():
        if any(kw in combined if " " in kw else kw in tokens for kw in keywords):
            matched_up.append(category)

    for category, keywords in _TRENDING_DOWN_MAP.items():
        if any(kw in combined if " " in kw else kw in tokens for kw in keywords):
            matched_down.append(category)

    up_count = len(matched_up)
    down_count = len(matched_down)

    # Relevance: how strongly does this align with up-trends?
    raw_relevance = min(up_count * _UP_WEIGHT - down_count * _DOWN_WEIGHT, _MAX_RELEVANCE)
    relevance_score = round(max(0.0, raw_relevance), 2)

    # Timing assessment
    if up_count >= 2 and down_count == 0:
        timing: Literal["EARLY", "OPTIMAL", "LATE"] = "EARLY"
    elif up_count > down_count:
        timing = "OPTIMAL"
    else:
        timing = "LATE"

    # Recommendation
    if timing == "EARLY":
        recommendation = (
            "Strong early-mover opportunity. Act now to establish position "
            "before the market becomes crowded."
        )
    elif timing == "OPTIMAL":
        recommendation = (
            "Good timing. Market is validated and growing. Focus on "
            "differentiation and rapid execution."
        )
    else:
        recommendation = (
            "Timing is challenging. Consider a sharper niche focus or a pivot "
            "toward emerging trend categories to improve positioning."
        )

    return TrendReport(
        trending_up=matched_up,
        trending_down=matched_down,
        relevance_score=relevance_score,
        timing_assessment=timing,
        recommendation=recommendation,
    )
