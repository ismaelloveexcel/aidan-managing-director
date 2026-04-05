"""
llm_scoring.py – LLM-augmented scoring path for ambiguous ideas.

When the keyword-based score lands in the 4.0–7.0 "ambiguous" range this
module calls the AIProvider's OpenAI reasoning client to evaluate each of the
five revenue dimensions with a structured prompt, then returns a ``ScoringResult``
that is a drop-in replacement for the standard ``RevenueScore``.

Falls back gracefully to the keyword-based scores when:
- The total keyword score is outside the ambiguous range.
- The AI provider is not configured (no API key).
- The LLM call raises any exception.
"""

from __future__ import annotations

import logging
from typing import Any

from app.integrations.ai_provider import AIProvider
from app.reasoning.scoring_engine import (
    DimensionScore,
    RevenueScore,
    ScoringDecision,
    score_idea,
)

logger = logging.getLogger(__name__)

# Range that triggers the LLM augmentation path.
_AMBIGUOUS_LOW = 4.0
_AMBIGUOUS_HIGH = 7.0

_SCORING_SYSTEM = (
    "You are a revenue scoring engine for AI-DAN, a monetization-first business "
    "decision system. You evaluate business ideas strictly on revenue potential. "
    "Be concise, critical, and commercially focused. Return only valid JSON."
)

_SCORING_PROMPT_TEMPLATE = """\
Score the following business idea on 5 revenue dimensions.
Each dimension must receive a score between 0.0 and 2.0 (decimals allowed).

Business idea: {idea_text}
Problem: {problem}
Target user: {target_user}
Monetization model: {monetization_model}
Competition level: {competition_level}
Build difficulty: {difficulty}
Time to revenue: {time_to_revenue}
Differentiation: {differentiation}

Respond with a JSON object in this exact format:
{{
  "demand": {{"score": <0-2>, "reason": "<brief reason>"}},
  "monetization": {{"score": <0-2>, "reason": "<brief reason>"}},
  "saturation": {{"score": <0-2>, "reason": "<brief reason (reverse: low saturation = high score)>"}},
  "complexity": {{"score": <0-2>, "reason": "<brief reason (reverse: low complexity = high score)>"}},
  "speed_to_revenue": {{"score": <0-2>, "reason": "<brief reason>"}}
}}
"""


def _clamp(value: float, lo: float = 0.0, hi: float = 2.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


def _parse_llm_dimensions(llm_json: dict[str, Any]) -> list[DimensionScore] | None:
    """Parse LLM JSON response into DimensionScore list.

    Returns None if the response is malformed so the caller can fall back.
    """
    expected = ("demand", "monetization", "saturation", "complexity", "speed_to_revenue")
    dimensions: list[DimensionScore] = []

    for name in expected:
        entry = llm_json.get(name)
        if not isinstance(entry, dict):
            return None
        try:
            score = _clamp(float(entry["score"]))
            reason = str(entry.get("reason", ""))
        except (KeyError, TypeError, ValueError):
            return None
        dimensions.append(DimensionScore(name=name, score=score, reason=reason))

    return dimensions


def score_idea_with_llm(
    *,
    idea_text: str,
    problem: str = "",
    target_user: str = "",
    monetization_model: str = "",
    competition_level: str = "",
    difficulty: str = "",
    time_to_revenue: str = "",
    differentiation: str = "",
    extra: dict[str, Any] | None = None,
    ai_provider: AIProvider,
) -> RevenueScore:
    """Score an idea using LLM augmentation for ambiguous keyword scores.

    Runs the standard keyword-based ``score_idea()`` first.  If the result
    falls in the 4.0–7.0 ambiguous range *and* the AI provider is available,
    a structured OpenAI prompt re-evaluates each dimension and the LLM scores
    replace the keyword scores.

    Falls back to the keyword result if the LLM path fails for any reason.

    Args:
        idea_text: Full idea description.
        problem: Problem statement.
        target_user: Target user description.
        monetization_model: Revenue model.
        competition_level: Market competition level.
        difficulty: Build difficulty.
        time_to_revenue: Expected time to first revenue.
        differentiation: Unique selling proposition.
        extra: Optional additional data (passed through unchanged).
        ai_provider: Configured AIProvider instance.

    Returns:
        RevenueScore with the same structure as ``score_idea()`` output.
    """
    # Step 1: baseline keyword scoring
    keyword_result = score_idea(
        idea_text=idea_text,
        problem=problem,
        target_user=target_user,
        monetization_model=monetization_model,
        competition_level=competition_level,
        difficulty=difficulty,
        time_to_revenue=time_to_revenue,
        differentiation=differentiation,
        extra=extra,
    )

    # Step 2: only augment if score is ambiguous and AI is available
    if not (_AMBIGUOUS_LOW <= keyword_result.total_score <= _AMBIGUOUS_HIGH):
        return keyword_result

    if not ai_provider.ai_enabled:
        logger.debug("llm_scoring: AI not configured; returning keyword result.")
        return keyword_result

    # Step 3: call LLM for enhanced scoring
    try:
        prompt = _SCORING_PROMPT_TEMPLATE.format(
            idea_text=idea_text,
            problem=problem,
            target_user=target_user,
            monetization_model=monetization_model,
            competition_level=competition_level,
            difficulty=difficulty,
            time_to_revenue=time_to_revenue,
            differentiation=differentiation,
        )

        llm_raw = ai_provider.openai.chat_json(
            prompt=prompt,
            system=_SCORING_SYSTEM,
            temperature=0.3,
            max_tokens=600,
        )

        if llm_raw.get("stub"):
            logger.debug("llm_scoring: LLM returned stub; falling back to keyword result.")
            return keyword_result

        dimensions = _parse_llm_dimensions(llm_raw)
        if dimensions is None:
            logger.warning("llm_scoring: Malformed LLM response; falling back.")
            return keyword_result

    except Exception:
        logger.warning("llm_scoring: LLM call failed; falling back to keyword scores.", exc_info=True)
        return keyword_result

    # Step 4: rebuild result from LLM dimensions
    total = min(sum(d.score for d in dimensions), 10.0)
    breakdown = {d.name: d.score for d in dimensions}

    if total >= 8.0:
        decision = ScoringDecision.APPROVE
        reason = f"Score {total:.1f}/10 — LLM-augmented: strong revenue potential. APPROVED for build."
    elif total >= 6.0:
        decision = ScoringDecision.HOLD
        reason = f"Score {total:.1f}/10 — LLM-augmented: moderate potential. HOLD for further validation."
    else:
        decision = ScoringDecision.REJECT
        reason = f"Score {total:.1f}/10 — LLM-augmented: insufficient revenue potential. REJECTED."

    return RevenueScore(
        total_score=total,
        decision=decision,
        dimensions=dimensions,
        breakdown=breakdown,
        decision_reason=reason,
    )

