"""
analyze.py – Idea analysis route (validation + delegation).

Accepts a business idea, delegates to the analysis service, and
returns a monetization-ready structured response.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_ai_provider
from app.reasoning.analyze_service import run_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Input payload for idea analysis."""

    idea: str = Field(min_length=3, description="The business idea to analyze.")


class MonetizationOutput(BaseModel):
    """Monetization-ready structured output."""

    # Core idea
    title: str = ""
    problem: str = ""
    target_user: str = ""
    solution: str = ""

    # Monetization
    monetization_method: str = ""
    pricing_suggestion: str = ""
    distribution_plan: str = ""
    first_10_users: str = ""
    competitive_edge: str = ""

    # Scores
    overall_score: float = 0.0
    feasibility_score: float = 0.0
    profitability_score: float = 0.0
    speed_score: float = 0.0
    competition_score: float = 0.0

    # Verdict
    verdict: str = ""
    why_now: str = ""
    main_risk: str = ""
    recommended_next_move: str = ""

    # Research
    market_research: str = ""

    # Source
    ai_powered: bool = False


class AnalyzeResponse(BaseModel):
    """Full analysis response."""

    success: bool = True
    analysis: MonetizationOutput = Field(default_factory=MonetizationOutput)
    pipeline_result: dict[str, Any] | None = None
    error: str | None = None


@router.post("/", response_model=AnalyzeResponse)
def analyze_idea(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a business idea using AI-DAN's full pipeline.

    Combines:
    1. Perplexity market research (when configured)
    2. OpenAI reasoning and structuring (when configured)
    3. Deterministic scoring pipeline (always)

    Returns a monetization-ready structured output.
    """
    result = run_analysis(request.idea, ai=get_ai_provider())

    return AnalyzeResponse(
        success=True,
        analysis=MonetizationOutput(**result["analysis"]),
        pipeline_result=result["pipeline_result"],
    )
