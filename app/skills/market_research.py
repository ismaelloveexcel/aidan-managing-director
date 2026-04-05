"""
market_research.py – Market research skill for agent invocation.

Thin wrapper around ``MarketResearchAgent`` that standardises the skill
interface and returns a typed ``MarketResearchSkillResult`` model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.market_researcher import MarketResearchAgent


class MarketResearchSkillResult(BaseModel):
    """Structured output from the market research skill."""

    vertical: str
    tam: str = Field(description="Total Addressable Market estimate")
    sam: str = Field(description="Serviceable Addressable Market estimate")
    som: str = Field(description="Serviceable Obtainable Market estimate")
    channels: list[str] = Field(default_factory=list, description="Recommended acquisition channels")
    growth_outlook: str = Field(description="Market growth outlook: LOW, MEDIUM, or HIGH")


def research_market(idea_text: str, target_user: str) -> MarketResearchSkillResult:
    """Run market research for an idea and return a structured result.

    Wraps ``MarketResearchAgent.research()`` and maps its output to the
    standardised ``MarketResearchSkillResult`` Pydantic model.

    Args:
        idea_text: The idea title or description.
        target_user: The intended user / customer segment.

    Returns:
        ``MarketResearchSkillResult`` with vertical, TAM/SAM/SOM, channels,
        and growth outlook.
    """
    agent = MarketResearchAgent()
    result = agent.research(
        idea_brief={
            "title": idea_text,
            "target_user": target_user,
        }
    )

    return MarketResearchSkillResult(
        vertical=result.vertical,
        tam=result.tam_estimate,
        sam=result.sam_estimate,
        som=result.som_estimate,
        channels=result.recommended_channels,
        growth_outlook=result.market_growth,
    )
