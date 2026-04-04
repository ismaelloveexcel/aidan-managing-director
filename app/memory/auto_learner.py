"""
auto_learner.py – Autonomous learning engine for AI-DAN.

Analyses accumulated feedback patterns, pricing objections, and
conversion blockers to produce deterministic scoring-weight and
pricing-recommendation updates.

This module is a PURE read/compute layer – it does NOT mutate the
MemoryStore; consumers decide what to persist.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.memory.store import LearningSignal, MemoryStore


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class ScoringWeightUpdate(BaseModel):
    """Deterministic scoring-weight adjustment recommendation."""

    factor: str
    current_weight: float = Field(ge=0.0, le=1.0)
    recommended_weight: float = Field(ge=0.0, le=1.0)
    reason: str


class PricingRecommendation(BaseModel):
    """Deterministic pricing adjustment recommendation."""

    project_id: str
    direction: str  # "reduce", "increase", "hold"
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ConversionBlocker(BaseModel):
    """Identified conversion blocker derived from feedback patterns."""

    project_id: str
    blocker_type: str
    occurrence_count: int
    recommendation: str


class AutoLearnerReport(BaseModel):
    """Full auto-learning report for a project."""

    project_id: str
    total_signals: int
    feedback_patterns: dict[str, int]
    pricing_objection_count: int
    messaging_issue_count: int
    not_needed_count: int
    scoring_weight_updates: list[ScoringWeightUpdate]
    pricing_recommendation: PricingRecommendation | None = None
    conversion_blockers: list[ConversionBlocker]
    prioritization_adjustment: str


# ---------------------------------------------------------------------------
# Auto-learner engine
# ---------------------------------------------------------------------------


class AutoLearner:
    """Analyses memory signals and produces deterministic learning recommendations."""

    # Default scoring weights (market_demand, pricing_fit, messaging_clarity).
    _DEFAULT_WEIGHTS: dict[str, float] = {
        "market_demand": 0.35,
        "pricing_fit": 0.35,
        "messaging_clarity": 0.30,
    }

    def __init__(self, memory_store: MemoryStore) -> None:
        self._memory = memory_store

    def analyse(self, project_id: str) -> AutoLearnerReport:
        """Produce a full learning report for *project_id*."""
        signals = self._memory.get_project_signals(project_id, limit=10_000)

        patterns = self._count_feedback_patterns(signals)
        pricing_objections = patterns.get("user_feedback_too_expensive", 0)
        messaging_issues = patterns.get("user_feedback_not_clear", 0)
        not_needed = patterns.get("user_feedback_not_needed", 0)
        payment_attempted = patterns.get("payment_attempted", 0)
        payment_success = patterns.get("payment_success", 0)

        weight_updates = self._compute_weight_updates(
            pricing_objections=pricing_objections,
            messaging_issues=messaging_issues,
            not_needed=not_needed,
            total=len(signals),
        )

        pricing_rec = self._compute_pricing_recommendation(
            project_id=project_id,
            pricing_objections=pricing_objections,
            payment_attempted=payment_attempted,
            payment_success=payment_success,
        )

        blockers = self._identify_conversion_blockers(
            project_id=project_id,
            patterns=patterns,
        )

        prioritization = self._compute_prioritization(
            payment_success=payment_success,
            not_needed=not_needed,
            total=len(signals),
        )

        return AutoLearnerReport(
            project_id=project_id,
            total_signals=len(signals),
            feedback_patterns=patterns,
            pricing_objection_count=pricing_objections,
            messaging_issue_count=messaging_issues,
            not_needed_count=not_needed,
            scoring_weight_updates=weight_updates,
            pricing_recommendation=pricing_rec,
            conversion_blockers=blockers,
            prioritization_adjustment=prioritization,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_feedback_patterns(signals: list[LearningSignal]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sig in signals:
            counts[sig.signal_type] = counts.get(sig.signal_type, 0) + 1
        return counts

    def _compute_weight_updates(
        self,
        *,
        pricing_objections: int,
        messaging_issues: int,
        not_needed: int,
        total: int,
    ) -> list[ScoringWeightUpdate]:
        updates: list[ScoringWeightUpdate] = []
        if total == 0:
            return updates

        pricing_ratio = pricing_objections / total
        messaging_ratio = messaging_issues / total
        demand_ratio = not_needed / total

        w = dict(self._DEFAULT_WEIGHTS)

        if pricing_ratio >= 0.3:
            new_w = min(w["pricing_fit"] + 0.10, 1.0)
            updates.append(
                ScoringWeightUpdate(
                    factor="pricing_fit",
                    current_weight=w["pricing_fit"],
                    recommended_weight=round(new_w, 2),
                    reason=f"{pricing_objections}/{total} signals are pricing objections (>= 30%).",
                ),
            )
            w["pricing_fit"] = new_w

        if messaging_ratio >= 0.25:
            new_w = min(w["messaging_clarity"] + 0.10, 1.0)
            updates.append(
                ScoringWeightUpdate(
                    factor="messaging_clarity",
                    current_weight=w["messaging_clarity"],
                    recommended_weight=round(new_w, 2),
                    reason=f"{messaging_issues}/{total} signals indicate unclear messaging (>= 25%).",
                ),
            )

        if demand_ratio >= 0.4:
            new_w = max(w["market_demand"] - 0.10, 0.0)
            updates.append(
                ScoringWeightUpdate(
                    factor="market_demand",
                    current_weight=w["market_demand"],
                    recommended_weight=round(new_w, 2),
                    reason=f"{not_needed}/{total} signals say 'not needed' (>= 40%) – downgrade demand weight.",
                ),
            )

        return updates

    @staticmethod
    def _compute_pricing_recommendation(
        *,
        project_id: str,
        pricing_objections: int,
        payment_attempted: int,
        payment_success: int,
    ) -> PricingRecommendation | None:
        if pricing_objections >= 3:
            return PricingRecommendation(
                project_id=project_id,
                direction="reduce",
                reason=f"{pricing_objections} pricing objection(s) recorded.",
                confidence=min(0.6 + pricing_objections * 0.05, 0.95),
            )
        if payment_attempted > 0 and payment_success == 0:
            return PricingRecommendation(
                project_id=project_id,
                direction="reduce",
                reason="Payments attempted but none succeeded – pricing or payment-flow issue.",
                confidence=0.80,
            )
        if payment_success > 0:
            return PricingRecommendation(
                project_id=project_id,
                direction="hold",
                reason="Payments succeeding – current pricing is working.",
                confidence=0.90,
            )
        return None

    @staticmethod
    def _identify_conversion_blockers(
        *,
        project_id: str,
        patterns: dict[str, int],
    ) -> list[ConversionBlocker]:
        blockers: list[ConversionBlocker] = []
        if patterns.get("user_feedback_too_expensive", 0) >= 2:
            blockers.append(
                ConversionBlocker(
                    project_id=project_id,
                    blocker_type="pricing",
                    occurrence_count=patterns["user_feedback_too_expensive"],
                    recommendation="Reduce price or add a lower-tier option.",
                ),
            )
        if patterns.get("user_feedback_not_clear", 0) >= 2:
            blockers.append(
                ConversionBlocker(
                    project_id=project_id,
                    blocker_type="messaging",
                    occurrence_count=patterns["user_feedback_not_clear"],
                    recommendation="Simplify landing page copy and CTA.",
                ),
            )
        if patterns.get("user_feedback_not_needed", 0) >= 2:
            blockers.append(
                ConversionBlocker(
                    project_id=project_id,
                    blocker_type="demand",
                    occurrence_count=patterns["user_feedback_not_needed"],
                    recommendation="Re-evaluate product-market fit.",
                ),
            )
        if patterns.get("payment_attempted", 0) >= 2 and patterns.get("payment_success", 0) == 0:
            blockers.append(
                ConversionBlocker(
                    project_id=project_id,
                    blocker_type="payment_flow",
                    occurrence_count=patterns["payment_attempted"],
                    recommendation="Audit checkout flow for friction or errors.",
                ),
            )
        return blockers

    @staticmethod
    def _compute_prioritization(
        *,
        payment_success: int,
        not_needed: int,
        total: int,
    ) -> str:
        if payment_success > 0:
            return "raise"
        if total > 0 and not_needed / total >= 0.5:
            return "lower"
        return "hold"
