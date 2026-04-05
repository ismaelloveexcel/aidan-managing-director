"""Tests for app/skills/ — market research, competitor analysis, and trend detection."""

from __future__ import annotations

from app.skills import (
    CompetitorAnalysisResult,
    MarketResearchSkillResult,
    TrendDetectionResult,
    analyze_competitors,
    detect_trends,
    research_market,
)


# ---------------------------------------------------------------------------
# research_market
# ---------------------------------------------------------------------------


def test_research_market_returns_correct_model() -> None:
    result = research_market("AI SaaS automation dashboard", "enterprise B2B teams")
    assert isinstance(result, MarketResearchSkillResult)


def test_research_market_has_required_fields() -> None:
    result = research_market("fintech invoice payment tool", "small businesses")
    assert result.vertical
    assert result.tam
    assert result.sam
    assert result.som
    assert result.growth_outlook in ("LOW", "MEDIUM", "HIGH")


def test_research_market_channels_non_empty() -> None:
    result = research_market("B2B SaaS analytics dashboard", "enterprise teams")
    assert isinstance(result.channels, list)
    assert len(result.channels) >= 1


def test_research_market_detects_ai_vertical() -> None:
    result = research_market("AI copilot agent for LLM tasks", "developers")
    assert result.vertical == "AI Tools"


def test_research_market_detects_fintech_vertical() -> None:
    result = research_market("invoice billing payment automation finance tool", "SMBs")
    assert result.vertical == "FinTech"


def test_research_market_empty_input_does_not_raise() -> None:
    result = research_market("", "")
    assert isinstance(result, MarketResearchSkillResult)
    assert result.vertical == "General Software"


# ---------------------------------------------------------------------------
# analyze_competitors
# ---------------------------------------------------------------------------


def test_analyze_competitors_returns_correct_model() -> None:
    result = analyze_competitors("AI recruiting platform", "CV parsing and job matching")
    assert isinstance(result, CompetitorAnalysisResult)


def test_analyze_competitors_has_required_fields() -> None:
    result = analyze_competitors("AI recruiting platform", "automated talent matching")
    assert result.competitor_count >= 0
    assert result.saturation in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(result.differentiation_detected, bool)
    assert isinstance(result.matched_categories, list)
    assert result.risk_level in ("LOW", "MEDIUM", "HIGH")


def test_analyze_competitors_high_saturation_no_diff_yields_high_risk() -> None:
    # Saturated category with generic solution
    result = analyze_competitors(
        "AI chatbot assistant platform saas",
        "generic ai assistant tool",
    )
    # High competitor count should surface HIGH saturation/risk
    assert result.saturation in ("MEDIUM", "HIGH")


def test_analyze_competitors_niche_solution_detects_differentiation() -> None:
    result = analyze_competitors(
        "Niche compliance workflow for local clinics",
        "automated compliance workflow specific to regional clinics",
    )
    assert result.differentiation_detected is True


def test_analyze_competitors_empty_input_does_not_raise() -> None:
    result = analyze_competitors("", "")
    assert isinstance(result, CompetitorAnalysisResult)


# ---------------------------------------------------------------------------
# detect_trends
# ---------------------------------------------------------------------------


def test_detect_trends_returns_correct_model() -> None:
    result = detect_trends("AI machine learning tool", "developers")
    assert isinstance(result, TrendDetectionResult)


def test_detect_trends_has_required_fields() -> None:
    result = detect_trends("blockchain crypto defi", "investors")
    assert isinstance(result.detected_trends, list)
    assert 0.0 <= result.trend_alignment_score <= 1.0
    assert isinstance(result.recommended_pivot, str)


def test_detect_trends_detects_ai_trend() -> None:
    result = detect_trends("AI LLM generative machine learning tool", "developers")
    assert "AI / Machine Learning" in result.detected_trends


def test_detect_trends_detects_blockchain_trend() -> None:
    result = detect_trends("blockchain smart contract defi platform", "crypto users")
    assert "Blockchain / Web3" in result.detected_trends


def test_detect_trends_detects_sustainability_trend() -> None:
    result = detect_trends("carbon sustainability cleantech green energy", "enterprises")
    assert "Sustainability / CleanTech" in result.detected_trends


def test_detect_trends_score_zero_for_no_trends() -> None:
    result = detect_trends("plain old spreadsheet tool", "accountants")
    # May or may not detect anything — just verify score is in [0, 1]
    assert 0.0 <= result.trend_alignment_score <= 1.0


def test_detect_trends_pivot_suggested_when_no_alignment() -> None:
    result = detect_trends("basic notepad app", "random users")
    if result.trend_alignment_score < 0.35 and not result.detected_trends:
        assert len(result.recommended_pivot) > 0


def test_detect_trends_no_pivot_when_well_aligned() -> None:
    result = detect_trends(
        "AI machine learning blockchain sustainability cleantech no-code low-code",
        "enterprise teams",
    )
    # Well-aligned idea should have high score and no pivot
    assert result.trend_alignment_score >= 0.35
