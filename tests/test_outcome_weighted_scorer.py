"""Tests for the outcome-weighted scoring engine."""

from __future__ import annotations

from app.reasoning.outcome_store import OutcomeRecord, OutcomeStore
from app.reasoning.outcome_weighted_scorer import (
    OutcomeWeightedScore,
    OutcomeWeightedScorer,
    _compute_adjustment,
)
from app.reasoning.outcome_store import SimilarOutcome


class TestComputeAdjustment:
    """Unit tests for the _compute_adjustment helper."""

    def test_no_neighbors_returns_zero_adjustment(self) -> None:
        adj = _compute_adjustment([])
        assert adj.adjustment == 0.0
        assert adj.neighbors_found == 0
        assert "no adjustment" in adj.explanation.lower()

    def test_high_outcome_produces_positive_adjustment(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=1.0)
        neighbors = [SimilarOutcome(record=record, similarity=1.0)]
        adj = _compute_adjustment(neighbors)
        assert adj.adjustment > 0.0

    def test_low_outcome_produces_negative_adjustment(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=0.0)
        neighbors = [SimilarOutcome(record=record, similarity=1.0)]
        adj = _compute_adjustment(neighbors)
        assert adj.adjustment < 0.0

    def test_neutral_outcome_produces_zero_adjustment(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=0.5)
        neighbors = [SimilarOutcome(record=record, similarity=1.0)]
        adj = _compute_adjustment(neighbors)
        assert adj.adjustment == 0.0

    def test_adjustment_clamped_at_max(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=1.0)
        neighbors = [SimilarOutcome(record=record, similarity=1.0)]
        adj = _compute_adjustment(neighbors)
        assert adj.adjustment <= 1.0

    def test_adjustment_clamped_at_min(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=0.0)
        neighbors = [SimilarOutcome(record=record, similarity=1.0)]
        adj = _compute_adjustment(neighbors)
        assert adj.adjustment >= -1.0

    def test_neighbors_found_count_is_correct(self) -> None:
        neighbors = [
            SimilarOutcome(
                record=OutcomeRecord(idea_id=str(i), idea_text="t", outcome_score=0.8),
                similarity=0.5,
            )
            for i in range(3)
        ]
        adj = _compute_adjustment(neighbors)
        assert adj.neighbors_found == 3

    def test_weighted_avg_uses_similarity_as_weight(self) -> None:
        # One high-similarity high-outcome neighbor and one low-similarity low-outcome.
        high = OutcomeRecord(idea_id="h", idea_text="test", outcome_score=1.0)
        low = OutcomeRecord(idea_id="l", idea_text="test", outcome_score=0.0)
        neighbors = [
            SimilarOutcome(record=high, similarity=0.9),
            SimilarOutcome(record=low, similarity=0.1),
        ]
        adj = _compute_adjustment(neighbors)
        # Weighted average should be dominated by the high-outcome neighbor.
        assert adj.avg_outcome_score > 0.5

    def test_explanation_populated(self) -> None:
        record = OutcomeRecord(idea_id="a", idea_text="test", outcome_score=0.8)
        neighbors = [SimilarOutcome(record=record, similarity=0.7)]
        adj = _compute_adjustment(neighbors)
        assert adj.explanation


class TestOutcomeWeightedScorer:
    """Unit tests for the OutcomeWeightedScorer class."""

    def setup_method(self) -> None:
        self.store = OutcomeStore()
        self.scorer = OutcomeWeightedScorer(self.store)

    def test_returns_outcome_weighted_score(self) -> None:
        result = self.scorer.score(idea_text="saas subscription platform")
        assert isinstance(result, OutcomeWeightedScore)

    def test_baseline_present_and_valid(self) -> None:
        result = self.scorer.score(idea_text="subscription platform for developers")
        assert result.baseline is not None
        assert 0.0 <= result.baseline.total_score <= 10.0

    def test_no_neighbors_zero_adjustment_and_equal_final(self) -> None:
        result = self.scorer.score(idea_text="completely unique unprecedented idea")
        assert result.adjustment.adjustment == 0.0
        assert result.final_score == result.baseline.total_score

    def test_good_outcomes_apply_positive_adjustment(self) -> None:
        for i in range(5):
            self.store.add_record(
                OutcomeRecord(
                    idea_id=f"good_{i}",
                    idea_text="subscription saas developer platform billing recurring",
                    outcome_score=1.0,
                ),
            )
        result = self.scorer.score(
            idea_text="subscription saas developer platform",
            monetization_model="billing recurring",
        )
        assert result.adjustment.adjustment >= 0.0

    def test_bad_outcomes_apply_negative_adjustment(self) -> None:
        for i in range(5):
            self.store.add_record(
                OutcomeRecord(
                    idea_id=f"bad_{i}",
                    idea_text="subscription saas developer platform billing recurring",
                    outcome_score=0.0,
                ),
            )
        result = self.scorer.score(
            idea_text="subscription saas developer platform",
            monetization_model="billing recurring",
        )
        assert result.adjustment.adjustment <= 0.0

    def test_final_score_clamped_to_valid_range(self) -> None:
        # Extremely positive outcomes should not push score above 10.
        for _ in range(10):
            self.store.add_record(
                OutcomeRecord(
                    idea_id="top",
                    idea_text="subscription saas billing recurring mrr developer",
                    outcome_score=1.0,
                ),
            )
        result = self.scorer.score(
            idea_text="subscription saas billing recurring mrr developer",
            monetization_model="subscription",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
        )
        assert 0.0 <= result.final_score <= 10.0

    def test_final_decision_consistent_with_final_score(self) -> None:
        result = self.scorer.score(
            idea_text="SaaS subscription platform for developers",
            problem="Developers waste time",
            target_user="Developers with strong demand",
            monetization_model="subscription recurring mrr",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
        )
        assert result.final_decision in {"approve", "hold", "reject"}
        if result.final_score >= 8.0:
            assert result.final_decision == "approve"
        elif result.final_score >= 6.0:
            assert result.final_decision == "hold"
        else:
            assert result.final_decision == "reject"

    def test_final_reason_populated(self) -> None:
        result = self.scorer.score(idea_text="some idea")
        assert result.final_reason
        assert "/10" in result.final_reason

    def test_adjustment_explanation_populated_when_neighbors_found(self) -> None:
        self.store.add_record(
            OutcomeRecord(idea_id="a", idea_text="saas subscription billing", outcome_score=0.8),
        )
        result = self.scorer.score(idea_text="saas subscription billing recurring")
        if result.adjustment.neighbors_found > 0:
            assert result.adjustment.explanation

    def test_accepts_all_score_idea_kwargs(self) -> None:
        result = self.scorer.score(
            idea_text="test idea",
            problem="problem",
            target_user="users",
            monetization_model="subscription",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
            differentiation="unique approach",
            extra={"custom_key": "value"},
        )
        assert isinstance(result, OutcomeWeightedScore)
