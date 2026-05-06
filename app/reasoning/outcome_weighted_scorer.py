"""
Outcome-weighted scoring engine (PR #14).

Wraps the baseline :func:`~app.reasoning.scoring_engine.score_idea` function
and blends aggregate outcome stats from historically similar ideas into the
final score.

How it works
------------
1. Run the baseline keyword scorer to get a ``RevenueScore``.
2. Query the :class:`~app.reasoning.outcome_store.OutcomeStore` for the
   *top_k* most-similar prior ideas (Jaccard similarity on text).
3. Compute a similarity-weighted average outcome score across those neighbors.
4. Derive a score adjustment: ``(avg_outcome - 0.5) × 2 × MAX_ADJUSTMENT``
   — clamped to ±1.0 point — and apply it to the baseline total.
5. Re-derive decision (approve/hold/reject) from the adjusted total.

The adjustment is intentionally small (±1 point on a 0-10 scale) so that
the data signal nudges rather than overrides the keyword-based score.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.reasoning.outcome_store import OutcomeStore, SimilarOutcome
from app.reasoning.scoring_engine import RevenueScore, score_idea

# Maximum adjustment (positive or negative) applied by historical outcome data.
_MAX_ADJUSTMENT: float = 1.0

# Minimum number of neighbors required before any adjustment is applied.
_MIN_NEIGHBORS: int = 1

# Only neighbors with at least this similarity contribute to the adjustment.
_SIMILARITY_THRESHOLD: float = 0.1


class OutcomeAdjustment(BaseModel):
    """Details of the outcome-based score adjustment."""

    neighbors_found: int = 0
    avg_outcome_score: float = 0.0
    adjustment: float = 0.0
    explanation: str = ""


class OutcomeWeightedScore(BaseModel):
    """Score enriched with historical outcome context."""

    baseline: RevenueScore
    adjustment: OutcomeAdjustment
    final_score: float = Field(ge=0.0, le=10.0)
    final_decision: str
    final_reason: str


class OutcomeWeightedScorer:
    """Wraps ``score_idea()`` with historical outcome context.

    Args:
        outcome_store: The shared store of historical idea outcomes.
    """

    def __init__(self, outcome_store: OutcomeStore) -> None:
        self._store = outcome_store

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
    ) -> OutcomeWeightedScore:
        """Score an idea using baseline + historical outcome adjustment.

        Args:
            idea_text: Full idea description.
            problem: Problem statement.
            target_user: Target user description.
            monetization_model: Revenue model.
            competition_level: Market competition level.
            difficulty: Build difficulty.
            time_to_revenue: Expected time to first revenue.
            differentiation: Unique selling proposition.
            extra: Optional additional data forwarded to ``score_idea``.

        Returns:
            :class:`OutcomeWeightedScore` containing baseline, adjustment, and
            the final outcome-adjusted score.
        """
        baseline = score_idea(
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

        query = " ".join(filter(None, [
            idea_text, problem, target_user, monetization_model, differentiation,
        ]))

        neighbors = self._store.find_similar(
            query,
            top_k=10,
            min_similarity=_SIMILARITY_THRESHOLD,
        )

        adjustment = _compute_adjustment(neighbors)
        raw_final = baseline.total_score + adjustment.adjustment
        final_score = round(min(10.0, max(0.0, raw_final)), 2)

        if final_score >= 8.0:
            final_decision = "approve"
            final_reason = f"Outcome-adjusted score {final_score:.1f}/10 — APPROVED."
        elif final_score >= 6.0:
            final_decision = "hold"
            final_reason = f"Outcome-adjusted score {final_score:.1f}/10 — HOLD."
        else:
            final_decision = "reject"
            final_reason = f"Outcome-adjusted score {final_score:.1f}/10 — REJECTED."

        return OutcomeWeightedScore(
            baseline=baseline,
            adjustment=adjustment,
            final_score=final_score,
            final_decision=final_decision,
            final_reason=final_reason,
        )


def _compute_adjustment(neighbors: list[SimilarOutcome]) -> OutcomeAdjustment:
    """Derive a score adjustment from similar historical outcomes.

    The adjustment formula is::

        raw = (weighted_avg_outcome - 0.5) × 2 × MAX_ADJUSTMENT

    This maps:
    - ``outcome=0.0`` → ``-MAX_ADJUSTMENT`` (strong negative signal)
    - ``outcome=0.5`` → ``0.0``             (neutral)
    - ``outcome=1.0`` → ``+MAX_ADJUSTMENT`` (strong positive signal)

    The result is clamped to ``[-MAX_ADJUSTMENT, +MAX_ADJUSTMENT]``.

    Args:
        neighbors: Similar historical outcomes retrieved from the store.

    Returns:
        :class:`OutcomeAdjustment` with the computed adjustment and
        a human-readable explanation.
    """
    if len(neighbors) < _MIN_NEIGHBORS:
        return OutcomeAdjustment(
            explanation="No similar historical outcomes found; no adjustment applied.",
        )

    total_weight = sum(n.similarity for n in neighbors)
    if total_weight == 0.0:
        return OutcomeAdjustment(
            neighbors_found=len(neighbors),
            explanation="Zero-weight neighbors; no adjustment applied.",
        )

    weighted_outcome = (
        sum(n.record.outcome_score * n.similarity for n in neighbors) / total_weight
    )

    raw_adj = (weighted_outcome - 0.5) * 2.0 * _MAX_ADJUSTMENT
    clamped = max(-_MAX_ADJUSTMENT, min(_MAX_ADJUSTMENT, raw_adj))

    if clamped > 0:
        direction = "upward"
    elif clamped < 0:
        direction = "downward"
    else:
        direction = "neutral"

    explanation = (
        f"Found {len(neighbors)} similar idea(s) with weighted avg outcome "
        f"{weighted_outcome:.2f}. Applying {direction} adjustment of "
        f"{clamped:+.2f} points."
    )

    return OutcomeAdjustment(
        neighbors_found=len(neighbors),
        avg_outcome_score=round(weighted_outcome, 4),
        adjustment=round(clamped, 4),
        explanation=explanation,
    )
