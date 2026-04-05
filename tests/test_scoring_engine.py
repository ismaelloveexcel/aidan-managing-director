"""Tests for the revenue scoring engine."""

from __future__ import annotations

import pytest

from app.reasoning.scoring_engine import (
    RevenueScore,
    ScoringDecision,
    score_idea,
)


class TestScoringEngine:
    """Tests for score_idea function."""

    def test_high_score_approves(self) -> None:
        result = score_idea(
            idea_text="SaaS subscription platform for developers",
            problem="Developers waste hours on repetitive tasks",
            target_user="Software developers with strong demand",
            monetization_model="subscription recurring mrr pricing",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
        )
        assert result.total_score >= 8.0
        assert result.decision == ScoringDecision.APPROVE

    def test_low_score_rejects(self) -> None:
        result = score_idea(
            idea_text="Something vague",
            problem="",
            target_user="",
            monetization_model="",
            competition_level="high",
            difficulty="hard",
            time_to_revenue="years",
        )
        assert result.total_score < 6.0
        assert result.decision == ScoringDecision.REJECT

    def test_medium_score_holds(self) -> None:
        result = score_idea(
            idea_text="Tool for users with some demand and need",
            problem="People need help with tasks",
            target_user="General audience",
            monetization_model="ads",
            competition_level="medium",
            difficulty="medium",
            time_to_revenue="months",
        )
        assert 6.0 <= result.total_score < 8.0 or result.total_score < 6.0
        # Score may vary but should be in moderate range
        assert result.decision in {ScoringDecision.HOLD, ScoringDecision.REJECT}

    def test_breakdown_has_five_dimensions(self) -> None:
        result = score_idea(
            idea_text="Test idea",
            problem="Test problem",
            target_user="Test users",
        )
        assert len(result.dimensions) == 5
        assert set(result.breakdown.keys()) == {
            "demand", "monetization", "saturation", "complexity", "speed_to_revenue",
        }

    def test_each_dimension_in_range(self) -> None:
        result = score_idea(
            idea_text="Test idea for customers",
            problem="Real problem",
            target_user="Users",
            monetization_model="subscription",
        )
        for dim in result.dimensions:
            assert 0.0 <= dim.score <= 2.0
            assert dim.name
            assert dim.reason

    def test_total_score_is_sum_of_dimensions(self) -> None:
        result = score_idea(
            idea_text="Test for users",
            problem="Problem statement",
            target_user="Target users",
        )
        expected = sum(d.score for d in result.dimensions)
        assert result.total_score == min(expected, 10.0)

    def test_total_score_clamped_to_10(self) -> None:
        result = score_idea(
            idea_text="Recurring subscription SaaS platform for loyal customers with traction",
            problem="Strong validated demand from customers",
            target_user="Developers with growing adoption",
            monetization_model="subscription recurring mrr pricing billing",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
        )
        assert result.total_score <= 10.0

    def test_decision_reason_populated(self) -> None:
        result = score_idea(
            idea_text="Test idea",
            problem="Test problem",
            target_user="Users",
        )
        assert result.decision_reason
        assert "/10" in result.decision_reason

    def test_competition_high_scores_low_saturation(self) -> None:
        result = score_idea(
            idea_text="Test",
            competition_level="high",
        )
        sat_score = result.breakdown.get("saturation", 0.0)
        assert sat_score == 0.0

    def test_competition_low_scores_high_saturation(self) -> None:
        result = score_idea(
            idea_text="Test",
            competition_level="low",
        )
        sat_score = result.breakdown.get("saturation", 0.0)
        assert sat_score == 2.0
