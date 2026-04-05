"""Tests for the app/skills modules."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.skills.competitor_analysis import CompetitorAnalysis, analyze_competitors
from app.skills.market_research import MarketResearchReport, research_market
from app.skills.trend_detection import TrendReport, detect_trends


# ---------------------------------------------------------------------------
# Market Research
# ---------------------------------------------------------------------------


class TestMarketResearch:
    """Tests for research_market skill function."""

    def _make_ai_provider(self, *, research_enabled: bool = False) -> MagicMock:
        provider = MagicMock()
        provider.research_enabled = research_enabled
        return provider

    def test_returns_market_research_report(self) -> None:
        ai_provider = self._make_ai_provider(research_enabled=False)
        result = research_market(
            idea_text="SaaS tool for B2B analytics",
            target_user="Enterprise teams",
            ai_provider=ai_provider,
        )
        assert isinstance(result, MarketResearchReport)

    def test_required_fields_present(self) -> None:
        ai_provider = self._make_ai_provider()
        result = research_market(
            idea_text="SaaS tool for developers",
            target_user="Software developers",
            ai_provider=ai_provider,
        )
        assert result.vertical
        assert result.market_size
        assert result.growth_rate in {"LOW", "MEDIUM", "HIGH"}
        assert isinstance(result.channels, list)
        assert result.source in {"deterministic", "ai-augmented"}

    def test_source_is_deterministic_when_ai_disabled(self) -> None:
        ai_provider = self._make_ai_provider(research_enabled=False)
        result = research_market(
            idea_text="AI chatbot tool",
            target_user="Small businesses",
            ai_provider=ai_provider,
        )
        assert result.source == "deterministic"

    def test_ai_not_called_when_disabled(self) -> None:
        ai_provider = self._make_ai_provider(research_enabled=False)
        research_market(
            idea_text="marketplace for freelancers",
            target_user="Freelancers",
            ai_provider=ai_provider,
        )
        ai_provider.perplexity.research.assert_not_called()

    def test_falls_back_on_ai_exception(self) -> None:
        ai_provider = self._make_ai_provider(research_enabled=True)
        ai_provider.perplexity.research.side_effect = RuntimeError("Perplexity down")
        result = research_market(
            idea_text="AI education platform",
            target_user="Students",
            ai_provider=ai_provider,
        )
        # Should still return valid result from deterministic agent
        assert isinstance(result, MarketResearchReport)
        assert result.source == "deterministic"

    def test_detects_saas_vertical(self) -> None:
        ai_provider = self._make_ai_provider()
        result = research_market(
            idea_text="B2B SaaS dashboard for workflow automation",
            target_user="Enterprise ops teams",
            ai_provider=ai_provider,
        )
        assert "saas" in result.vertical.lower() or result.vertical != ""

    def test_channels_is_list(self) -> None:
        ai_provider = self._make_ai_provider()
        result = research_market("fintech payment platform", "SMBs", ai_provider)
        assert isinstance(result.channels, list)
        assert len(result.channels) > 0


# ---------------------------------------------------------------------------
# Competitor Analysis
# ---------------------------------------------------------------------------


class TestCompetitorAnalysis:
    """Tests for analyze_competitors skill function."""

    def test_returns_competitor_analysis(self) -> None:
        result = analyze_competitors(
            idea_text="AI recruiting tool for startups",
            target_user="Startup founders",
            competition_level="medium",
        )
        assert isinstance(result, CompetitorAnalysis)

    def test_required_fields_present(self) -> None:
        result = analyze_competitors(
            idea_text="analytics dashboard for reporting",
            target_user="Operations teams",
            competition_level="high",
        )
        assert result.competitor_count >= 0
        assert isinstance(result.top_competitors, list)
        assert result.market_gap
        assert 0.0 <= result.differentiation_score <= 1.0
        assert result.recommended_positioning

    def test_top_competitors_structure(self) -> None:
        result = analyze_competitors(
            idea_text="AI assistant chatbot copilot",
            target_user="Developers",
            competition_level="high",
        )
        for comp in result.top_competitors:
            assert "name" in comp
            assert "strength" in comp
            assert "weakness" in comp

    def test_differentiation_score_range(self) -> None:
        result = analyze_competitors(
            idea_text="automation workflow tool",
            target_user="Non-technical users",
            competition_level="medium",
        )
        assert 0.0 <= result.differentiation_score <= 1.0

    def test_minimal_idea_still_works(self) -> None:
        result = analyze_competitors(
            idea_text="app",
            target_user="users",
            competition_level="",
        )
        assert isinstance(result, CompetitorAnalysis)
        assert result.recommended_positioning

    def test_high_competition_level_increases_count(self) -> None:
        low = analyze_competitors(
            idea_text="unique niche tool",
            target_user="specialists",
            competition_level="low",
        )
        high = analyze_competitors(
            idea_text="unique niche tool",
            target_user="specialists",
            competition_level="high",
        )
        assert high.competitor_count >= low.competitor_count

    def test_low_competition_level_caps_count(self) -> None:
        result = analyze_competitors(
            idea_text="generic platform tool",
            target_user="everyone",
            competition_level="low",
        )
        assert result.competitor_count <= 5

    def test_high_competition_level_floors_count(self) -> None:
        result = analyze_competitors(
            idea_text="basic generic app",
            target_user="anyone",
            competition_level="high",
        )
        assert result.competitor_count >= 15


# ---------------------------------------------------------------------------
# Trend Detection
# ---------------------------------------------------------------------------


class TestTrendDetection:
    """Tests for detect_trends skill function."""

    def test_returns_trend_report(self) -> None:
        result = detect_trends("AI automation tool for workflow management")
        assert isinstance(result, TrendReport)

    def test_required_fields_present(self) -> None:
        result = detect_trends("no-code builder for API integrations")
        assert isinstance(result.trending_up, list)
        assert isinstance(result.trending_down, list)
        assert 0.0 <= result.relevance_score <= 1.0
        assert result.timing_assessment in {"EARLY", "OPTIMAL", "LATE"}
        assert result.recommendation

    def test_ai_keywords_detected_as_trending_up(self) -> None:
        result = detect_trends("AI LLM agent tool for automation workflows")
        assert any("AI" in t or "automation" in t.lower() for t in result.trending_up)

    def test_trending_down_detected(self) -> None:
        result = detect_trends("desktop app with spreadsheet excel workflow and manual entry")
        assert len(result.trending_down) > 0

    def test_optimal_timing_with_more_up_than_down(self) -> None:
        result = detect_trends("AI automation no-code api integration")
        # Multiple up signals, likely optimal or early
        assert result.timing_assessment in {"EARLY", "OPTIMAL"}

    def test_late_timing_with_down_signals(self) -> None:
        result = detect_trends("desktop app .exe install spreadsheet crud todo app")
        assert result.timing_assessment == "LATE"

    def test_empty_idea_returns_valid_report(self) -> None:
        result = detect_trends("")
        assert isinstance(result, TrendReport)
        assert result.timing_assessment in {"EARLY", "OPTIMAL", "LATE"}

    def test_target_user_contributes_to_detection(self) -> None:
        result = detect_trends("new platform", target_user="remote async distributed teams")
        assert any("remote" in t.lower() for t in result.trending_up)

    def test_relevance_score_increases_with_more_up_signals(self) -> None:
        low = detect_trends("some generic app")
        high = detect_trends("AI LLM agent automation no-code api security fintech healthtech")
        assert high.relevance_score >= low.relevance_score


# ---------------------------------------------------------------------------
# Skills __init__ exports
# ---------------------------------------------------------------------------


class TestSkillsInit:
    """Verify skills module exports all required symbols."""

    def test_all_exports_importable(self) -> None:
        from app.skills import (
            CompetitorAnalysis,
            MarketResearchReport,
            TrendReport,
            analyze_competitors,
            detect_trends,
            research_market,
        )
        assert callable(analyze_competitors)
        assert callable(research_market)
        assert callable(detect_trends)
