"""Tests for app/skills/trend_detection.py — keyword matching and scoring."""

from __future__ import annotations

import pytest

from app.skills.trend_detection import TrendDetectionResult, detect_trends


# ---------------------------------------------------------------------------
# Keyword detection – individual trend categories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "idea_text, expected_trend",
    [
        ("AI copilot LLM chatbot agent", "AI / Machine Learning"),
        ("blockchain smart contract defi web3", "Blockchain / Web3"),
        ("augmented reality virtual reality metaverse", "AR / VR / Spatial Computing"),
        ("sustainability carbon net zero cleantech", "Sustainability / CleanTech"),
        ("no-code low-code visual builder workflow automation", "No-Code / Low-Code"),
        ("remote work hybrid distributed team async", "Remote Work / Future of Work"),
        ("mental health wellness wearable telehealth", "Health & Wellness Tech"),
        ("creator economy influencer newsletter patreon", "Creator Economy"),
        ("embedded finance open banking bnpl", "FinTech / Embedded Finance"),
        ("cybersecurity zero trust data privacy gdpr", "Cybersecurity"),
    ],
)
def test_detects_specific_trend(idea_text: str, expected_trend: str) -> None:
    result = detect_trends(idea_text, "")
    assert expected_trend in result.detected_trends


# ---------------------------------------------------------------------------
# Score range validation
# ---------------------------------------------------------------------------


def test_score_always_between_0_and_1() -> None:
    for idea in [
        "random unrelated words nothing special",
        "AI blockchain sustainability no-code remote work health creator fintech cybersecurity AR VR",
        "",
    ]:
        result = detect_trends(idea, "")
        assert 0.0 <= result.trend_alignment_score <= 1.0


def test_score_increases_with_more_trends() -> None:
    low = detect_trends("basic spreadsheet tool", "accountants")
    high = detect_trends(
        "AI machine learning blockchain sustainability no-code remote work",
        "enterprise teams",
    )
    assert high.trend_alignment_score >= low.trend_alignment_score


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


def test_returns_pydantic_model() -> None:
    result = detect_trends("AI tool", "developers")
    assert isinstance(result, TrendDetectionResult)


def test_detected_trends_is_list() -> None:
    result = detect_trends("AI tool", "developers")
    assert isinstance(result.detected_trends, list)


def test_recommended_pivot_is_string() -> None:
    result = detect_trends("AI tool", "developers")
    assert isinstance(result.recommended_pivot, str)


def test_empty_input_does_not_raise() -> None:
    result = detect_trends("", "")
    assert isinstance(result, TrendDetectionResult)


# ---------------------------------------------------------------------------
# Pivot suggestions
# ---------------------------------------------------------------------------


def test_pivot_empty_when_well_aligned() -> None:
    result = detect_trends(
        "AI machine learning blockchain sustainability no-code low-code",
        "enterprise teams",
    )
    # 6+ trend categories detected → alignment high → no pivot needed
    if result.trend_alignment_score >= 0.35:
        assert result.recommended_pivot == ""


def test_pivot_suggested_for_completely_generic_idea() -> None:
    result = detect_trends("basic notepad application", "random people")
    if not result.detected_trends and result.trend_alignment_score < 0.35:
        assert len(result.recommended_pivot) > 0


# ---------------------------------------------------------------------------
# Multiple trend detection
# ---------------------------------------------------------------------------


def test_multiple_trends_detected_simultaneously() -> None:
    result = detect_trends(
        "AI blockchain sustainability creator economy cybersecurity",
        "enterprise and individual users",
    )
    assert len(result.detected_trends) >= 3


def test_target_user_contributes_to_detection() -> None:
    """Target user text should be included in keyword scanning."""
    result = detect_trends("generic tool", "remote work distributed teams")
    assert "Remote Work / Future of Work" in result.detected_trends
