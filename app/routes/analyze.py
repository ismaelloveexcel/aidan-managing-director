"""
analyze.py – AI-powered idea analysis endpoint for the UI.

Accepts a business idea, runs it through the full AI-DAN pipeline
(research → evaluate → structure → output), and returns a rich
monetization-ready response.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import get_ai_provider
from app.reasoning.strategist import Strategist

router = APIRouter()

_strategist = Strategist()


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
async def analyze_idea(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a business idea using AI-DAN's full pipeline.

    Combines:
    1. Perplexity market research (when configured)
    2. OpenAI reasoning and structuring (when configured)
    3. Deterministic scoring pipeline (always)

    Returns a monetization-ready structured output.
    """
    ai = get_ai_provider()

    # Run deterministic pipeline for structured scoring
    pipeline_result = _strategist.process_founder_input(request.idea)
    pipeline_dict = pipeline_result.model_dump(mode="json")

    # Also generate an idea directly for field extraction
    from app.reasoning.idea_engine import IdeaEngine
    from app.planning.distribution import generate_distribution_plan

    idea = IdeaEngine().generate(request.idea)
    dist_dict = generate_distribution_plan(
        target_user=idea.target_user,
        title=idea.title,
        problem=idea.problem,
    )

    # Run AI-powered analysis if available
    ai_analysis: dict[str, Any] = {}
    research_context = ""

    if ai.research_enabled:
        try:
            research_context = ai.perplexity.research(
                f"Market research for this business idea: {request.idea}"
            )
        except Exception:
            research_context = ""

    if ai.ai_enabled:
        try:
            ai_analysis = ai.analyze_idea(request.idea, research_context=research_context)
        except Exception:
            ai_analysis = {}

    # Merge AI output with deterministic pipeline output
    score = pipeline_dict.get("score") or {}
    breakdown = score.get("breakdown") or {}
    total = float(score.get("total_score", 0) or 0)
    decision_output = pipeline_dict.get("decision_output") or {}

    # Build meaningful scores even when pipeline gate rejects
    # (use heuristic scores from idea attributes as baseline)
    from app.reasoning.models import Difficulty
    base_feasibility = 7.0 if idea.difficulty == Difficulty.LOW else (5.0 if idea.difficulty == Difficulty.MEDIUM else 3.0)
    base_speed = 8.0 if "week" in idea.time_to_launch.lower() else 5.0
    base_profitability = 7.0 if "subscription" in idea.monetization_path.lower() else 5.0
    base_competition = 6.0

    analysis = MonetizationOutput(
        title=ai_analysis.get("title", idea.title),
        problem=ai_analysis.get("problem", idea.problem),
        target_user=ai_analysis.get("target_user", idea.target_user),
        solution=ai_analysis.get("solution", idea.summary),
        monetization_method=ai_analysis.get("monetization_method", idea.monetization_path),
        pricing_suggestion=ai_analysis.get("pricing_suggestion", idea.monetization_path),
        distribution_plan=ai_analysis.get("distribution_plan", dist_dict.get("primary_channel", "Direct outreach")),
        first_10_users=ai_analysis.get("first_10_users", dist_dict.get("first_10_users_plan", "Manual outreach to target communities")),
        competitive_edge=ai_analysis.get("competitive_edge", "Speed to market and focused feature set"),
        overall_score=float(ai_analysis.get("overall_score", total if total > 0 else round((base_feasibility + base_speed + base_profitability + base_competition) / 4, 1))),
        feasibility_score=float(ai_analysis.get("feasibility_score", breakdown.get("build_complexity", 0) * 5 or base_feasibility)),
        profitability_score=float(ai_analysis.get("profitability_score", breakdown.get("monetization_potential", 0) * 5 or base_profitability)),
        speed_score=float(ai_analysis.get("speed_score", breakdown.get("speed_to_revenue", 0) * 5 or base_speed)),
        competition_score=float(ai_analysis.get("competition_score", breakdown.get("competition_saturation", 0) * 5 or base_competition)),
        verdict=ai_analysis.get("verdict", score.get("decision", "HOLD") if total > 0 else "HOLD"),
        why_now=ai_analysis.get("why_now", decision_output.get("why_now", "Evaluate timing based on market conditions.")),
        main_risk=ai_analysis.get("main_risk", decision_output.get("main_risk", "Market validation needed before scaling.")),
        recommended_next_move=ai_analysis.get("recommended_next_move", pipeline_dict.get("suggested_next_action", "Validate with 5 potential customers.")),
        market_research=research_context,
        ai_powered=ai.ai_enabled,
    )

    return AnalyzeResponse(
        success=True,
        analysis=analysis,
        pipeline_result=pipeline_dict,
    )
