"""Tests for the A/B scoring harness."""

from __future__ import annotations

import os


from app.reasoning.ab_harness import (
    ABHarness,
    ABScoringResult,
    FEATURE_FLAG_OUTCOME_WEIGHTED,
)
from app.reasoning.outcome_store import OutcomeRecord, OutcomeStore


class TestABHarnessFeatureFlag:
    """Tests for feature-flag reading behaviour."""

    def test_flag_off_by_default_when_not_in_dict(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store)
        # No dict override, no env var set → should be False.
        env_key = f"FEATURE_{FEATURE_FLAG_OUTCOME_WEIGHTED.upper()}"
        os.environ.pop(env_key, None)
        assert not harness.is_variant_active()

    def test_flag_off_explicit_false(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store, feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False})
        assert not harness.is_variant_active()

    def test_flag_on_explicit_true(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store, feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: True})
        assert harness.is_variant_active()

    def test_set_flag_toggles_state(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store, feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False})
        harness.set_flag(FEATURE_FLAG_OUTCOME_WEIGHTED, True)
        assert harness.is_variant_active()
        harness.set_flag(FEATURE_FLAG_OUTCOME_WEIGHTED, False)
        assert not harness.is_variant_active()

    def test_env_var_activates_flag(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store)  # no dict override
        env_key = f"FEATURE_{FEATURE_FLAG_OUTCOME_WEIGHTED.upper()}"
        try:
            os.environ[env_key] = "true"
            assert harness.is_variant_active()
        finally:
            os.environ.pop(env_key, None)

    def test_dict_override_wins_over_env_var(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store, feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False})
        env_key = f"FEATURE_{FEATURE_FLAG_OUTCOME_WEIGHTED.upper()}"
        try:
            os.environ[env_key] = "true"
            # Dict override (False) should win over env var (true).
            assert not harness.is_variant_active()
        finally:
            os.environ.pop(env_key, None)


class TestABHarnessScoringFlagOff:
    """Tests for ABHarness.score() when the feature flag is OFF."""

    def setup_method(self) -> None:
        self.store = OutcomeStore()
        self.harness = ABHarness(
            self.store,
            feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False},
        )

    def test_returns_ab_scoring_result(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert isinstance(result, ABScoringResult)

    def test_variant_active_is_false(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant_active is False

    def test_variant_is_none(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant is None

    def test_delta_is_none(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.delta is None

    def test_active_score_equals_baseline(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.active_score == result.baseline.total_score

    def test_active_decision_equals_baseline_decision(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.active_decision == result.baseline.decision.value

    def test_feature_flag_field_set_correctly(self) -> None:
        result = self.harness.score(idea_text="test idea")
        assert result.feature_flag == FEATURE_FLAG_OUTCOME_WEIGHTED


class TestABHarnessScoringFlagOn:
    """Tests for ABHarness.score() when the feature flag is ON."""

    def setup_method(self) -> None:
        self.store = OutcomeStore()
        self.harness = ABHarness(
            self.store,
            feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: True},
        )

    def test_returns_ab_scoring_result(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert isinstance(result, ABScoringResult)

    def test_variant_active_is_true(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant_active is True

    def test_variant_is_not_none(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant is not None

    def test_delta_is_not_none(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.delta is not None

    def test_delta_equals_variant_minus_baseline(self) -> None:
        self.store.add_record(
            OutcomeRecord(
                idea_id="hist1",
                idea_text="saas subscription platform developer tool billing",
                outcome_score=0.9,
            ),
        )
        result = self.harness.score(idea_text="saas subscription platform developer")
        assert result.variant is not None
        expected = round(result.variant.final_score - result.baseline.total_score, 4)
        assert abs(result.delta - expected) < 1e-6  # type: ignore[operator]

    def test_active_score_equals_variant_final(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant is not None
        assert result.active_score == result.variant.final_score

    def test_active_decision_equals_variant_final_decision(self) -> None:
        result = self.harness.score(idea_text="saas subscription platform")
        assert result.variant is not None
        assert result.active_decision == result.variant.final_decision

    def test_accepts_all_score_kwargs(self) -> None:
        result = self.harness.score(
            idea_text="test idea",
            problem="test problem",
            target_user="users",
            monetization_model="subscription",
            competition_level="low",
            difficulty="easy",
            time_to_revenue="days",
            differentiation="unique",
            extra={"meta": "value"},
        )
        assert isinstance(result, ABScoringResult)


class TestABHarnessDivergenceStats:
    """Tests for the divergence statistics tracking."""

    def test_divergence_stats_initially_empty(self) -> None:
        harness = ABHarness(OutcomeStore())
        stats = harness.divergence_stats()
        assert stats["comparisons_run"] == 0
        assert stats["avg_absolute_delta"] == 0.0

    def test_flag_off_does_not_increment_comparison_count(self) -> None:
        harness = ABHarness(
            OutcomeStore(),
            feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False},
        )
        harness.score(idea_text="saas platform")
        harness.score(idea_text="subscription tool")
        assert harness.divergence_stats()["comparisons_run"] == 0

    def test_flag_on_increments_comparison_count(self) -> None:
        harness = ABHarness(
            OutcomeStore(),
            feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: True},
        )
        harness.score(idea_text="saas platform")
        harness.score(idea_text="subscription tool")
        assert harness.divergence_stats()["comparisons_run"] == 2

    def test_avg_absolute_delta_is_non_negative(self) -> None:
        harness = ABHarness(
            OutcomeStore(),
            feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: True},
        )
        for _ in range(5):
            harness.score(idea_text="saas subscription platform")
        stats = harness.divergence_stats()
        assert stats["avg_absolute_delta"] >= 0.0

    def test_toggle_flag_mid_session(self) -> None:
        store = OutcomeStore()
        harness = ABHarness(store, feature_flags={FEATURE_FLAG_OUTCOME_WEIGHTED: False})
        harness.score(idea_text="idea one")        # flag off — not counted
        harness.set_flag(FEATURE_FLAG_OUTCOME_WEIGHTED, True)
        harness.score(idea_text="idea two")        # flag on — counted
        harness.score(idea_text="idea three")      # flag on — counted
        assert harness.divergence_stats()["comparisons_run"] == 2
