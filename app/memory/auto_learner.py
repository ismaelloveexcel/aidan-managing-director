"""
Auto-learning system that tracks success/failure patterns and adjusts scoring weights.

Records outcomes from factory runs, feedback decisions, and distribution results.
Uses these signals to recommend scoring weight adjustments over time.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.memory.store import LearningSignal, MemoryStore

# Canonical set of allowed outcome types.
OutcomeType = Literal[
    "build_success",
    "build_failure",
    "revenue_detected",
    "no_traction",
    "conversion_high",
    "conversion_low",
    "pricing_validated",
    "distribution_success",
    "distribution_failure",
]

OUTCOME_TYPES: frozenset[str] = frozenset(OutcomeType.__args__)  # type: ignore[attr-defined]

SUCCESS_TYPES: frozenset[str] = frozenset({
    "build_success",
    "revenue_detected",
    "conversion_high",
    "pricing_validated",
    "distribution_success",
})

FAILURE_TYPES: frozenset[str] = frozenset({
    "build_failure",
    "no_traction",
    "conversion_low",
    "distribution_failure",
})


class ScoringWeights(BaseModel):
    """Adjustable scoring weights derived from learning signals."""

    demand: float = Field(default=1.0, ge=0.5, le=2.0)
    willingness_to_pay: float = Field(default=1.0, ge=0.5, le=2.0)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    saturation: float = Field(default=1.0, ge=0.5, le=2.0)
    complexity: float = Field(default=1.0, ge=0.5, le=2.0)
    distribution: float = Field(default=1.0, ge=0.5, le=2.0)


class LearningInsight(BaseModel):
    """Aggregated insight from auto-learning signals."""

    total_signals: int = 0
    success_rate: float = 0.0
    top_success_pattern: str | None = None
    top_failure_pattern: str | None = None
    pricing_performance: dict[str, float] = Field(default_factory=dict)
    distribution_performance: dict[str, float] = Field(default_factory=dict)
    recommended_weights: ScoringWeights = Field(default_factory=ScoringWeights)


class AutoLearner:
    """Tracks success/failure patterns and recommends scoring adjustments."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self._memory = memory_store
        self._weights = ScoringWeights()

    @property
    def current_weights(self) -> ScoringWeights:
        """Return current scoring weights."""
        return self._weights.model_copy()

    def record_outcome(
        self,
        *,
        project_id: str,
        outcome_type: OutcomeType,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a project outcome as a learning signal.

        Args:
            project_id: The project that produced this outcome.
            outcome_type: Must be one of the canonical OutcomeType values.
            score: Normalized score 0.0–1.0 representing outcome quality.
            metadata: Optional details (pricing_model, channel, etc.).

        Raises:
            ValueError: If *outcome_type* is not a recognised outcome.
        """
        if outcome_type not in OUTCOME_TYPES:
            raise ValueError(
                f"Invalid outcome_type '{outcome_type}'. "
                f"Must be one of: {', '.join(sorted(OUTCOME_TYPES))}",
            )

        clamped_score = min(1.0, max(0.0, score))
        notes_parts = [f"outcome={outcome_type}"]
        if metadata:
            for key, value in sorted(metadata.items()):
                notes_parts.append(f"{key}={value}")

        self._memory.record_signal(
            LearningSignal(
                project_id=project_id,
                signal_type=outcome_type,
                score=clamped_score,
                notes="; ".join(notes_parts),
            ),
        )
        self._memory.record_event(
            {
                "event_type": "auto_learning",
                "project_id": project_id,
                "outcome_type": outcome_type,
                "score": clamped_score,
                "metadata": metadata or {},
            },
        )

    def generate_insight(self) -> LearningInsight:
        """Aggregate all learning signals into actionable insight."""
        events = self._memory.recent_events(limit=2000)
        learning_events = [e for e in events if e.get("event_type") == "auto_learning"]

        if not learning_events:
            return LearningInsight(recommended_weights=self._weights.model_copy())

        success_types = SUCCESS_TYPES
        failure_types = FAILURE_TYPES

        success_count = 0
        failure_count = 0
        pattern_counts: dict[str, int] = {}
        success_patterns: dict[str, int] = {}
        failure_patterns: dict[str, int] = {}
        pricing_scores: dict[str, list[float]] = {}
        distribution_scores: dict[str, list[float]] = {}

        for event in learning_events:
            outcome = event.get("outcome_type", "")
            score = float(event.get("score", 0.0))
            meta = event.get("metadata", {})

            pattern_counts[outcome] = pattern_counts.get(outcome, 0) + 1

            if outcome in success_types:
                success_count += 1
                success_patterns[outcome] = success_patterns.get(outcome, 0) + 1
            elif outcome in failure_types:
                failure_count += 1
                failure_patterns[outcome] = failure_patterns.get(outcome, 0) + 1

            pricing_model = meta.get("pricing_model")
            if pricing_model:
                pricing_scores.setdefault(pricing_model, []).append(score)

            channel = meta.get("channel")
            if channel:
                distribution_scores.setdefault(channel, []).append(score)

        total = success_count + failure_count
        success_rate = round(success_count / total, 2) if total > 0 else 0.0

        top_success = max(success_patterns, key=success_patterns.get) if success_patterns else None
        top_failure = max(failure_patterns, key=failure_patterns.get) if failure_patterns else None

        pricing_perf = {
            model: round(sum(scores) / len(scores), 2)
            for model, scores in pricing_scores.items()
            if scores
        }
        dist_perf = {
            ch: round(sum(scores) / len(scores), 2)
            for ch, scores in distribution_scores.items()
            if scores
        }

        weights = self._compute_adjusted_weights(
            success_rate=success_rate,
            pricing_perf=pricing_perf,
            dist_perf=dist_perf,
        )
        self._weights = weights

        return LearningInsight(
            total_signals=len(learning_events),
            success_rate=success_rate,
            top_success_pattern=top_success,
            top_failure_pattern=top_failure,
            pricing_performance=pricing_perf,
            distribution_performance=dist_perf,
            recommended_weights=weights,
        )

    @staticmethod
    def _compute_adjusted_weights(
        *,
        success_rate: float,
        pricing_perf: dict[str, float],
        dist_perf: dict[str, float],
    ) -> ScoringWeights:
        """Derive adjusted scoring weights from historical performance."""
        demand_w = 1.0
        wtp_w = 1.0
        speed_w = 1.0
        saturation_w = 1.0
        complexity_w = 1.0
        distribution_w = 1.0

        if success_rate < 0.3:
            demand_w = 1.3
            saturation_w = 1.4
        elif success_rate > 0.7:
            speed_w = 1.2
            distribution_w = 1.2

        if pricing_perf:
            avg_pricing = sum(pricing_perf.values()) / len(pricing_perf)
            if avg_pricing < 0.4:
                wtp_w = 1.4
            elif avg_pricing > 0.7:
                wtp_w = 0.8

        if dist_perf:
            avg_dist = sum(dist_perf.values()) / len(dist_perf)
            if avg_dist < 0.4:
                distribution_w = max(distribution_w, 1.3)

        return ScoringWeights(
            demand=round(min(2.0, max(0.5, demand_w)), 2),
            willingness_to_pay=round(min(2.0, max(0.5, wtp_w)), 2),
            speed=round(min(2.0, max(0.5, speed_w)), 2),
            saturation=round(min(2.0, max(0.5, saturation_w)), 2),
            complexity=round(min(2.0, max(0.5, complexity_w)), 2),
            distribution=round(min(2.0, max(0.5, distribution_w)), 2),
        )
