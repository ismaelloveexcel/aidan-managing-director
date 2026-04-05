"""
competitor_analysis.py – Competitor analysis skill for agent invocation.

Thin wrapper around ``GuardianAgent.assess_competition()`` that standardises
the skill interface and returns a typed ``CompetitorAnalysisResult`` model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.guardian import GuardianAgent


class CompetitorAnalysisResult(BaseModel):
    """Structured output from the competitor analysis skill."""

    competitor_count: int = Field(ge=0, description="Estimated number of direct competitors")
    saturation: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Market saturation level")
    differentiation_detected: bool = Field(description="Whether meaningful differentiation was found")
    matched_categories: list[str] = Field(
        default_factory=list,
        description="Market categories matched during analysis",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Overall competitive risk level")


def analyze_competitors(idea_text: str, solution: str) -> CompetitorAnalysisResult:
    """Analyse the competitive landscape for an idea.

    Wraps ``GuardianAgent.assess_competition()`` and maps its output to the
    standardised ``CompetitorAnalysisResult`` Pydantic model.

    Args:
        idea_text: The idea title or description.
        solution: The proposed solution or product approach.

    Returns:
        ``CompetitorAnalysisResult`` with competitor count, saturation,
        differentiation flag, matched categories, and risk level.
    """
    agent = GuardianAgent()
    heuristic = agent.assess_competition(
        build_brief={
            "title": idea_text,
            "solution": solution,
        }
    )

    # Derive a composite risk level from saturation and differentiation
    if heuristic.market_saturation == "HIGH" and not heuristic.differentiation_detected:
        risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    elif heuristic.market_saturation == "LOW":
        risk_level = "LOW"
    else:
        risk_level = "MEDIUM"

    return CompetitorAnalysisResult(
        competitor_count=heuristic.competitor_count,
        saturation=heuristic.market_saturation,
        differentiation_detected=heuristic.differentiation_detected,
        matched_categories=heuristic.matched_categories,
        risk_level=risk_level,
    )
