"""
Deterministic decision policy for project performance evaluation.
"""

from __future__ import annotations

from app.feedback.models import DecisionResult


def decide(*, visits: int, conversion_rate: float, revenue: float) -> DecisionResult:
    """Apply deterministic decision rules from the Phase 3 specification.

    Thresholds:
    - Kill: visits >= 100, conversion < 1%, revenue = 0
    - Scale: revenue > 0, conversion >= 3%
    - Revise: visits >= 100, conversion < 3%
    - Monitor: default fallback
    """
    if visits >= 100 and conversion_rate < 0.01 and revenue == 0:
        return DecisionResult(
            decision="kill_candidate",
            reason="Traffic is sufficient but conversion is below 1% with no revenue.",
            next_action="Prepare stop plan and only continue if next snapshot materially improves.",
            confidence=0.9,
            suggested_next_state="killed",
            suggested_next_action="stop project",
        )
    if revenue > 0 and conversion_rate >= 0.03:
        return DecisionResult(
            decision="scale_candidate",
            reason="Revenue is positive and conversion is at or above 3%.",
            next_action="Increase distribution and prioritize feature expansion.",
            confidence=0.88,
            suggested_next_state="scaled",
            suggested_next_action="scale project",
        )
    if visits >= 100 and conversion_rate < 0.03:
        return DecisionResult(
            decision="revise_candidate",
            reason="Traffic exists but conversion is below 3%.",
            next_action="Revise messaging/CTA and rerun validation cycle.",
            confidence=0.8,
            suggested_next_state="monitoring",
            suggested_next_action="revise experiment",
        )
    return DecisionResult(
        decision="monitor",
        reason="Insufficient deterministic signal for revise/scale/kill.",
        next_action="Continue collecting metrics and avoid lifecycle changes.",
        confidence=0.65,
        suggested_next_state="monitoring",
        suggested_next_action="collect more data",
    )
