"""
analyze_service.py – Orchestration logic for AI-powered idea analysis.

Coordinates the deterministic pipeline, IdeaEngine, distribution plan,
and optional AI enrichment (OpenAI + Perplexity) into a single
structured result.  Keeps routes thin (validation + delegation only).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.integrations.ai_provider import AIProvider
from app.planning.distribution import generate_distribution_plan
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import Difficulty
from app.reasoning.strategist import Strategist

logger = logging.getLogger(__name__)

# Baseline scores by difficulty / attribute (0-10 scale)
_SCORE_LOW_DIFFICULTY = 7.0
_SCORE_MED_DIFFICULTY = 5.0
_SCORE_HIGH_DIFFICULTY = 3.0
_SCORE_FAST_LAUNCH = 8.0
_SCORE_SLOW_LAUNCH = 5.0
_SCORE_SUBSCRIPTION = 7.0
_SCORE_OTHER_MONETIZATION = 5.0
_SCORE_COMPETITION_DEFAULT = 6.0
# Pipeline breakdown scores are 0-2; multiply to convert to 0-10 scale.
_BREAKDOWN_SCALE = 5

_DIFFICULTY_SCORES = {
    Difficulty.LOW: _SCORE_LOW_DIFFICULTY,
    Difficulty.MEDIUM: _SCORE_MED_DIFFICULTY,
    Difficulty.HIGH: _SCORE_HIGH_DIFFICULTY,
}

_strategist = Strategist()
_idea_engine = IdeaEngine()


def _scaled_or_base(breakdown: dict[str, Any], key: str, base: float) -> float:
    """Scale a 0-2 pipeline breakdown value to 0-10, or fall back to *base*."""
    raw = breakdown.get(key, 0) or 0
    scaled = raw * _BREAKDOWN_SCALE
    return scaled if scaled > 0 else base


def run_analysis(idea_text: str, ai: AIProvider) -> dict[str, Any]:
    """Run the full analysis pipeline for a business idea.

    Returns a dict with ``analysis`` (structured output), ``pipeline_result``
    (raw pipeline dict), and ``ai_powered`` (bool).
    """
    # 1. Deterministic pipeline
    pipeline_result = _strategist.process_founder_input(idea_text)
    pipeline_dict = pipeline_result.model_dump(mode="json")

    # 2. Idea + distribution (field extraction)
    idea = _idea_engine.generate(idea_text)
    dist_dict = generate_distribution_plan(
        target_user=idea.target_user,
        title=idea.title,
        problem=idea.problem,
    )

    # 3. Optional AI enrichment
    ai_analysis: dict[str, Any] = {}
    research_context = ""
    ai_actually_used = False

    if ai.research_enabled:
        try:
            research_context = ai.perplexity.research(
                f"Market research for this business idea: {idea_text}"
            )
        except (httpx.HTTPError, KeyError, IndexError):
            logger.exception("Perplexity research failed for idea: %s", idea_text[:100])
            research_context = ""

    if ai.ai_enabled:
        try:
            ai_analysis = ai.analyze_idea(idea_text, research_context=research_context)
            # Mark as AI-powered only if the result is NOT a stub fallback
            if not ai_analysis.get("stub"):
                ai_actually_used = True
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            logger.exception("OpenAI analysis failed for idea: %s", idea_text[:100])
            ai_analysis = {}

    # 4. Merge deterministic + AI output
    score = pipeline_dict.get("score") or {}
    breakdown = score.get("breakdown") or {}
    total = float(score.get("total_score", 0) or 0)
    decision_output = pipeline_dict.get("decision_output") or {}

    base_feasibility = _DIFFICULTY_SCORES.get(idea.difficulty, _SCORE_MED_DIFFICULTY)
    base_speed = _SCORE_FAST_LAUNCH if "week" in idea.time_to_launch.lower() else _SCORE_SLOW_LAUNCH
    base_profitability = (
        _SCORE_SUBSCRIPTION
        if "subscription" in idea.monetization_path.lower()
        else _SCORE_OTHER_MONETIZATION
    )
    base_competition = _SCORE_COMPETITION_DEFAULT

    overall_fallback = round(
        (base_feasibility + base_speed + base_profitability + base_competition) / 4,
        1,
    )

    analysis = {
        "title": ai_analysis.get("title", idea.title),
        "problem": ai_analysis.get("problem", idea.problem),
        "target_user": ai_analysis.get("target_user", idea.target_user),
        "solution": ai_analysis.get("solution", idea.summary),
        "monetization_method": ai_analysis.get("monetization_method", idea.monetization_path),
        "pricing_suggestion": ai_analysis.get("pricing_suggestion", idea.monetization_path),
        "distribution_plan": ai_analysis.get(
            "distribution_plan",
            dist_dict.get("primary_channel", "Direct outreach"),
        ),
        "first_10_users": ai_analysis.get(
            "first_10_users",
            dist_dict.get("first_10_users_plan", "Manual outreach to target communities"),
        ),
        "competitive_edge": ai_analysis.get(
            "competitive_edge", "Speed to market and focused feature set"
        ),
        "overall_score": float(
            ai_analysis.get("overall_score", total if total > 0 else overall_fallback)
        ),
        "feasibility_score": float(
            ai_analysis.get(
                "feasibility_score",
                _scaled_or_base(breakdown, "build_complexity", base_feasibility),
            )
        ),
        "profitability_score": float(
            ai_analysis.get(
                "profitability_score",
                _scaled_or_base(breakdown, "monetization_potential", base_profitability),
            )
        ),
        "speed_score": float(
            ai_analysis.get(
                "speed_score",
                _scaled_or_base(breakdown, "speed_to_revenue", base_speed),
            )
        ),
        "competition_score": float(
            ai_analysis.get(
                "competition_score",
                _scaled_or_base(breakdown, "competition_saturation", base_competition),
            )
        ),
        "verdict": ai_analysis.get(
            "verdict", score.get("decision", "HOLD") if total > 0 else "HOLD"
        ),
        "why_now": ai_analysis.get(
            "why_now",
            decision_output.get("why_now", "Evaluate timing based on market conditions."),
        ),
        "main_risk": ai_analysis.get(
            "main_risk",
            decision_output.get("main_risk", "Market validation needed before scaling."),
        ),
        "recommended_next_move": ai_analysis.get(
            "recommended_next_move",
            pipeline_dict.get("suggested_next_action", "Validate with 5 potential customers."),
        ),
        "market_research": research_context,
        "ai_powered": ai_actually_used,
    }

    return {
        "analysis": analysis,
        "pipeline_result": pipeline_dict,
    }
