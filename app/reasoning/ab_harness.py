"""
A/B harness for rolling out outcome-weighted scoring (PR #14).

Compares the baseline :func:`~app.reasoning.scoring_engine.score_idea`
against the :class:`~app.reasoning.outcome_weighted_scorer.OutcomeWeightedScorer`
behind a feature flag so that production traffic can be gradually shifted once
real outcome data has accumulated.

Feature flag
------------
The flag ``outcome_weighted_scoring_enabled`` is checked in this priority order:

1. The ``feature_flags`` dict supplied to :class:`ABHarness` (runtime/test override).
2. The environment variable ``FEATURE_OUTCOME_WEIGHTED_SCORING_ENABLED``
   (set to ``"1"``, ``"true"``, or ``"yes"`` to activate).
3. Default: **disabled** (baseline scoring only).

Divergence tracking
-------------------
When the variant is active, :meth:`ABHarness.score` accumulates per-call
``|variant_score - baseline_score|`` deltas.  Call
:meth:`ABHarness.divergence_stats` to retrieve aggregate statistics for
monitoring and gate-rollout decisions.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from pydantic import BaseModel, Field

from app.reasoning.outcome_store import OutcomeStore
from app.reasoning.outcome_weighted_scorer import OutcomeWeightedScore, OutcomeWeightedScorer
from app.reasoning.scoring_engine import RevenueScore, score_idea

# Canonical feature-flag name used by this harness.
FEATURE_FLAG_OUTCOME_WEIGHTED: str = "outcome_weighted_scoring_enabled"


class ABScoringResult(BaseModel):
    """Result produced by the A/B harness for a single scoring request."""

    baseline: RevenueScore
    variant: OutcomeWeightedScore | None = None
    active_score: float = Field(ge=0.0, le=10.0)
    active_decision: str
    delta: float | None = None  # variant.final_score − baseline.total_score
    variant_active: bool = False
    feature_flag: str = FEATURE_FLAG_OUTCOME_WEIGHTED


class ABHarness:
    """A/B harness comparing baseline scoring against outcome-weighted scoring.

    When the feature flag is **off** (the default), only the baseline scorer
    runs and the variant fields are ``None``.

    When the feature flag is **on**, both scorers run, the variant result is
    returned as the active score, and the delta is recorded for monitoring.

    Args:
        outcome_store: The shared :class:`~app.reasoning.outcome_store.OutcomeStore`
            used by the outcome-weighted scorer.
        feature_flags: Optional dict of flag overrides (useful for tests).
    """

    def __init__(
        self,
        outcome_store: OutcomeStore,
        *,
        feature_flags: dict[str, bool] | None = None,
    ) -> None:
        self._scorer = OutcomeWeightedScorer(outcome_store)
        self._flags: dict[str, bool] = dict(feature_flags or {})
        self._lock = threading.Lock()
        self._comparison_count: int = 0
        self._total_delta: float = 0.0

    # ------------------------------------------------------------------
    # Feature-flag helpers
    # ------------------------------------------------------------------

    def is_variant_active(self) -> bool:
        """Return ``True`` when the outcome-weighted variant should be used."""
        with self._lock:
            if FEATURE_FLAG_OUTCOME_WEIGHTED in self._flags:
                return self._flags[FEATURE_FLAG_OUTCOME_WEIGHTED]
        env_key = f"FEATURE_{FEATURE_FLAG_OUTCOME_WEIGHTED.upper()}"
        return os.environ.get(env_key, "false").lower() in {"1", "true", "yes"}

    def set_flag(self, flag: str, enabled: bool) -> None:
        """Set a feature flag at runtime (also useful for tests).

        Args:
            flag: Flag name (e.g. ``FEATURE_FLAG_OUTCOME_WEIGHTED``).
            enabled: New boolean value.
        """
        with self._lock:
            self._flags[flag] = enabled

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score(
        self,
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
    ) -> ABScoringResult:
        """Score an idea through the baseline (and optionally the variant).

        The *active* score returned is:

        * The baseline score when the feature flag is **off**.
        * The outcome-weighted score when the flag is **on**.

        Args:
            idea_text: Full idea description.
            problem: Problem statement.
            target_user: Target user description.
            monetization_model: Revenue model.
            competition_level: Market competition level.
            difficulty: Build difficulty.
            time_to_revenue: Expected time to first revenue.
            differentiation: Unique selling proposition.
            extra: Optional extra data forwarded to the scorers.

        Returns:
            :class:`ABScoringResult` with baseline, optional variant, and
            the active score/decision.
        """
        shared_kwargs: dict[str, Any] = dict(
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

        baseline = score_idea(**shared_kwargs)

        if not self.is_variant_active():
            return ABScoringResult(
                baseline=baseline,
                variant=None,
                active_score=baseline.total_score,
                active_decision=baseline.decision.value,
                delta=None,
                variant_active=False,
            )

        variant = self._scorer.score(**shared_kwargs)
        delta = round(variant.final_score - baseline.total_score, 4)

        with self._lock:
            self._comparison_count += 1
            self._total_delta += abs(delta)

        return ABScoringResult(
            baseline=baseline,
            variant=variant,
            active_score=variant.final_score,
            active_decision=variant.final_decision,
            delta=delta,
            variant_active=True,
        )

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def divergence_stats(self) -> dict[str, Any]:
        """Return aggregate A/B divergence statistics.

        Returns:
            Dict with:
            - ``comparisons_run``: total variant-active calls recorded.
            - ``avg_absolute_delta``: mean ``|variant - baseline|`` across
              all variant-active calls.
        """
        with self._lock:
            count = self._comparison_count
            total_delta = self._total_delta
        return {
            "comparisons_run": count,
            "avg_absolute_delta": round(total_delta / count, 4) if count > 0 else 0.0,
        }
