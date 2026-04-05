"""
market_research.py – Reusable market research skill.

Combines the deterministic MarketResearchAgent with optional Perplexity-based
real market data enrichment via AIProvider.  Always falls back gracefully to
the deterministic baseline when AI is unavailable or raises an error.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.market_researcher import MarketResearchAgent, MarketResearchResult
from app.integrations.ai_provider import AIProvider

logger = logging.getLogger(__name__)


class MarketResearchReport(BaseModel):
    """Structured output from the market research skill."""

    vertical: str
    market_size: str
    growth_rate: Literal["LOW", "MEDIUM", "HIGH"]
    competitors: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    source: Literal["deterministic", "ai-augmented"]


_AGENT = MarketResearchAgent()

_RESEARCH_PROMPT_TEMPLATE = (
    "Provide concise market research for this business idea.\n\n"
    "Idea: {idea_text}\n"
    "Target user: {target_user}\n\n"
    "Return a JSON object with:\n"
    '  "competitors": [list of 3-5 real competitor names],\n'
    '  "opportunities": [list of 2-3 market opportunities as short strings]\n'
)


def research_market(
    idea_text: str,
    target_user: str,
    ai_provider: AIProvider,
) -> MarketResearchReport:
    """Research a market using deterministic baseline plus optional AI enrichment.

    Uses :class:`~app.agents.market_researcher.MarketResearchAgent` for the
    deterministic baseline.  When ``ai_provider.research_enabled`` is True,
    calls Perplexity to enrich competitor names and opportunities.  Falls back
    to deterministic-only if the AI call fails.

    Args:
        idea_text: Full description of the idea.
        target_user: Description of the target user.
        ai_provider: Configured AIProvider instance.

    Returns:
        MarketResearchReport with vertical, market_size, growth_rate,
        competitors, opportunities, channels, and source.
    """
    idea_brief = {"idea": idea_text, "target_user": target_user}
    baseline: MarketResearchResult = _AGENT.research(idea_brief=idea_brief)

    # Default data from deterministic agent
    competitors: list[str] = []
    opportunities: list[str] = [
        f"Growing {baseline.vertical} market with {baseline.market_growth} growth.",
        "Early mover advantage available for focused vertical solutions.",
    ]
    source: Literal["deterministic", "ai-augmented"] = "deterministic"

    # Try AI enrichment if Perplexity is available
    if ai_provider.research_enabled:
        try:
            prompt = _RESEARCH_PROMPT_TEMPLATE.format(
                idea_text=idea_text,
                target_user=target_user,
            )
            raw = ai_provider.perplexity.research(prompt)
            if raw and not raw.startswith("Configure"):
                import json  # noqa: PLC0415

                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed.get("competitors"), list):
                        competitors = [str(c) for c in parsed["competitors"][:5]]
                    if isinstance(parsed.get("opportunities"), list):
                        opportunities = [str(o) for o in parsed["opportunities"][:3]]
                    source = "ai-augmented"
                except (json.JSONDecodeError, TypeError):
                    logger.debug("market_research: Could not parse AI response as JSON.")
        except Exception:
            logger.warning("market_research: AI enrichment failed; using deterministic result.", exc_info=True)

    return MarketResearchReport(
        vertical=baseline.vertical,
        market_size=baseline.tam_estimate,
        growth_rate=baseline.market_growth,
        competitors=competitors,
        opportunities=opportunities,
        channels=baseline.recommended_channels,
        source=source,
    )
