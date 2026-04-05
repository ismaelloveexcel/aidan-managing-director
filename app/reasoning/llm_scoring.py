"""
llm_scoring.py – LLM-augmented scoring path for ambiguous idea scores.

When the keyword-based scoring engine returns a score in the 4–7 "ambiguous"
range, this module provides an optional LLM re-scoring path that uses GPT to
evaluate each scoring dimension individually.  Falls back gracefully when no
API key is configured.
"""

from __future__ import annotations

import logging
import re

from app.integrations.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Scoring dimensions with their descriptions for the LLM prompt
_DIMENSIONS: list[str] = [
    "demand",
    "monetization",
    "saturation",
    "complexity",
    "speed_to_revenue",
]

_DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "demand": "How strong is real, proven demand for this idea? (0 = no evidence, 2 = strong evidence)",
    "monetization": "How clear and viable is the monetization path? (0 = unclear, 2 = strong, proven model)",
    "saturation": (
        "How low is market saturation? Rate INVERSELY — 0 = extremely crowded/saturated, "
        "2 = underserved niche with little competition"
    ),
    "complexity": (
        "How low is build complexity? Rate INVERSELY — 0 = extremely complex to build, "
        "2 = simple, can be built in days/weeks"
    ),
    "speed_to_revenue": "How fast can this generate revenue? (0 = months/years away, 2 = revenue possible within weeks)",
}


def llm_score_dimension(
    client: OpenAIClient,
    *,
    dimension_name: str,
    idea_text: str,
    problem: str,
    target_user: str,
) -> tuple[float, str]:
    """Score a single idea dimension using the LLM.

    Builds a focused system prompt asking GPT to score 0–2 on a specific
    dimension with a one-sentence justification.  Falls back to (0.0,
    "LLM unavailable") on any error or when no API key is configured.

    Args:
        client: Configured ``OpenAIClient`` instance.
        dimension_name: One of the five scoring dimensions.
        idea_text: The idea title or short description.
        problem: The problem being solved.
        target_user: The intended user/customer.

    Returns:
        Tuple of ``(score, reason)`` where score is 0.0–2.0.
    """
    description = _DIMENSION_DESCRIPTIONS.get(
        dimension_name,
        f"Evaluate the '{dimension_name}' dimension on a 0–2 scale.",
    )

    system_prompt = (
        "You are a senior venture analyst scoring startup ideas. "
        "You MUST respond with exactly two lines:\n"
        "SCORE: <number between 0.0 and 2.0>\n"
        "REASON: <one sentence justification>\n"
        "No other text."
    )

    user_prompt = (
        f"Dimension: {dimension_name}\n"
        f"Description: {description}\n\n"
        f"Idea: {idea_text}\n"
        f"Problem solved: {problem}\n"
        f"Target user: {target_user}\n\n"
        "Score this dimension 0.0–2.0 and give a one-sentence reason."
    )

    if not client.is_configured:
        return (0.0, "LLM unavailable")

    try:
        response = client.chat(user_prompt, system=system_prompt, temperature=0.2, max_tokens=100)
        return _parse_llm_dimension_response(response)
    except Exception as exc:  # pragma: no cover – network/API failures
        logger.warning("LLM dimension scoring failed for '%s': %s", dimension_name, exc)
        return (0.0, "LLM unavailable")


def _parse_llm_dimension_response(response: str) -> tuple[float, str]:
    """Parse the two-line LLM response into a (score, reason) tuple.

    Expected format::

        SCORE: 1.5
        REASON: Strong niche demand with limited direct competition.

    Falls back to (0.0, "parse error") when the expected format is absent.
    """
    score = 0.0
    reason = "parse error"

    score_match = re.search(r"SCORE:\s*([\d.]+)", response, re.IGNORECASE)
    reason_match = re.search(r"REASON:\s*(.+)", response, re.IGNORECASE)

    if score_match:
        try:
            raw = float(score_match.group(1))
            score = max(0.0, min(2.0, raw))
        except ValueError:
            pass

    if reason_match:
        reason = reason_match.group(1).strip()

    return (score, reason)


def llm_augmented_score(
    client: OpenAIClient,
    *,
    idea_text: str,
    problem: str,
    target_user: str,
    keyword_score: float,
    keyword_dimensions: list,
) -> dict:
    """Re-score an idea via LLM when the keyword score is in the ambiguous range.

    Only activates when ``keyword_score`` is between 4.0 and 7.0 (inclusive).
    Outside that range the function returns immediately with
    ``{"augmented": False, "reason": "score outside ambiguous range"}``.

    Args:
        client: Configured ``OpenAIClient`` instance.
        idea_text: The idea title or short description.
        problem: The problem being solved.
        target_user: The intended user/customer.
        keyword_score: The existing deterministic keyword-based total score.
        keyword_dimensions: List of dimension dicts from the keyword scorer
            (used to preserve dimension names in the output).

    Returns:
        Dict with ``llm_total_score``, ``llm_dimensions``, ``augmented=True``
        when activated; or ``{"augmented": False, "reason": ...}`` otherwise.
    """
    if not (4.0 <= keyword_score <= 7.0):
        return {"augmented": False, "reason": "score outside ambiguous range"}

    llm_dimensions: list[dict] = []
    total = 0.0

    for dim_name in _DIMENSIONS:
        score, reason = llm_score_dimension(
            client,
            dimension_name=dim_name,
            idea_text=idea_text,
            problem=problem,
            target_user=target_user,
        )
        llm_dimensions.append({"dimension": dim_name, "score": score, "reason": reason})
        total += score

    return {
        "llm_total_score": round(total, 2),
        "llm_dimensions": llm_dimensions,
        "augmented": True,
    }
