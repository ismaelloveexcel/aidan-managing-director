"""Tests for app/reasoning/llm_scoring.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.reasoning.llm_scoring import (
    _parse_llm_dimension_response,
    llm_augmented_score,
    llm_score_dimension,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unconfigured_client() -> MagicMock:
    """Return a mock OpenAIClient with is_configured=False."""
    client = MagicMock()
    client.is_configured = False
    return client


def _configured_client(response: str = "SCORE: 1.5\nREASON: Good demand signal.") -> MagicMock:
    """Return a mock OpenAIClient with is_configured=True and a canned response."""
    client = MagicMock()
    client.is_configured = True
    client.chat.return_value = response
    return client


# ---------------------------------------------------------------------------
# _parse_llm_dimension_response
# ---------------------------------------------------------------------------


def test_parse_valid_response() -> None:
    score, reason = _parse_llm_dimension_response("SCORE: 1.5\nREASON: Strong demand signal.")
    assert score == 1.5
    assert reason == "Strong demand signal."


def test_parse_clamps_score_above_2() -> None:
    score, _ = _parse_llm_dimension_response("SCORE: 3.0\nREASON: Too high.")
    assert score == 2.0


def test_parse_clamps_score_below_0() -> None:
    score, _ = _parse_llm_dimension_response("SCORE: -1.0\nREASON: Too low.")
    assert score == 0.0


def test_parse_missing_score_returns_zero() -> None:
    score, reason = _parse_llm_dimension_response("No score here.")
    assert score == 0.0
    assert reason == "parse error"


def test_parse_missing_reason_returns_parse_error() -> None:
    _, reason = _parse_llm_dimension_response("SCORE: 1.0")
    assert reason == "parse error"


def test_parse_case_insensitive() -> None:
    score, reason = _parse_llm_dimension_response("score: 2.0\nreason: Perfect.")
    assert score == 2.0
    assert reason == "Perfect."


# ---------------------------------------------------------------------------
# llm_score_dimension
# ---------------------------------------------------------------------------


def test_score_dimension_returns_fallback_when_unconfigured() -> None:
    client = _unconfigured_client()
    score, reason = llm_score_dimension(
        client,
        dimension_name="demand",
        idea_text="AI SaaS tool",
        problem="slow workflows",
        target_user="enterprise teams",
    )
    assert score == 0.0
    assert reason == "LLM unavailable"


def test_score_dimension_returns_parsed_score_when_configured() -> None:
    client = _configured_client("SCORE: 1.8\nREASON: Clear demand in B2B space.")
    score, reason = llm_score_dimension(
        client,
        dimension_name="monetization",
        idea_text="Subscription SaaS",
        problem="manual billing",
        target_user="SMBs",
    )
    assert score == 1.8
    assert "demand" in reason.lower() or len(reason) > 0


# ---------------------------------------------------------------------------
# llm_augmented_score – outside range guard
# ---------------------------------------------------------------------------


def test_returns_not_augmented_for_score_below_4() -> None:
    client = _configured_client()
    result = llm_augmented_score(
        client,
        idea_text="A test idea",
        problem="a problem",
        target_user="users",
        keyword_score=3.5,
        keyword_dimensions=[],
    )
    assert result["augmented"] is False
    assert result["reason"] == "score outside ambiguous range"


def test_returns_not_augmented_for_score_above_7() -> None:
    client = _configured_client()
    result = llm_augmented_score(
        client,
        idea_text="A test idea",
        problem="a problem",
        target_user="users",
        keyword_score=7.5,
        keyword_dimensions=[],
    )
    assert result["augmented"] is False
    assert result["reason"] == "score outside ambiguous range"


def test_returns_not_augmented_for_exactly_3_9() -> None:
    client = _configured_client()
    result = llm_augmented_score(
        client,
        idea_text="Idea",
        problem="p",
        target_user="u",
        keyword_score=3.9,
        keyword_dimensions=[],
    )
    assert result["augmented"] is False


# ---------------------------------------------------------------------------
# llm_augmented_score – within range (mocked LLM)
# ---------------------------------------------------------------------------


def test_augmented_score_structure_for_ambiguous_score() -> None:
    client = _configured_client("SCORE: 1.5\nREASON: Good signal.")
    result = llm_augmented_score(
        client,
        idea_text="AI productivity tool",
        problem="slow work",
        target_user="knowledge workers",
        keyword_score=5.0,
        keyword_dimensions=[],
    )
    assert result["augmented"] is True
    assert "llm_total_score" in result
    assert "llm_dimensions" in result
    assert isinstance(result["llm_total_score"], float)
    assert isinstance(result["llm_dimensions"], list)
    assert len(result["llm_dimensions"]) == 5  # 5 scoring dimensions


def test_augmented_score_dimensions_have_required_keys() -> None:
    client = _configured_client("SCORE: 1.0\nREASON: Moderate.")
    result = llm_augmented_score(
        client,
        idea_text="SaaS tool",
        problem="complexity",
        target_user="developers",
        keyword_score=6.0,
        keyword_dimensions=[],
    )
    for dim in result["llm_dimensions"]:
        assert "dimension" in dim
        assert "score" in dim
        assert "reason" in dim


def test_augmented_score_boundary_at_4() -> None:
    """Score of exactly 4.0 is in range."""
    client = _configured_client("SCORE: 1.0\nREASON: Ok.")
    result = llm_augmented_score(
        client,
        idea_text="Idea",
        problem="p",
        target_user="u",
        keyword_score=4.0,
        keyword_dimensions=[],
    )
    assert result["augmented"] is True


def test_augmented_score_boundary_at_7() -> None:
    """Score of exactly 7.0 is in range."""
    client = _configured_client("SCORE: 1.0\nREASON: Ok.")
    result = llm_augmented_score(
        client,
        idea_text="Idea",
        problem="p",
        target_user="u",
        keyword_score=7.0,
        keyword_dimensions=[],
    )
    assert result["augmented"] is True


def test_augmented_score_falls_back_gracefully_when_unconfigured() -> None:
    """Unconfigured client returns 0.0 per dimension but still produces a valid structure."""
    client = _unconfigured_client()
    result = llm_augmented_score(
        client,
        idea_text="Some idea",
        problem="some problem",
        target_user="some users",
        keyword_score=5.5,
        keyword_dimensions=[],
    )
    assert result["augmented"] is True
    assert result["llm_total_score"] == 0.0
    assert all(d["score"] == 0.0 for d in result["llm_dimensions"])
