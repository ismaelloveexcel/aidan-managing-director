"""
Deterministic decision policy for project performance evaluation.

Supports original conversion-based rules plus payment-signal and
user-feedback overrides from the revenue intelligence layer.
"""

from __future__ import annotations

from app.feedback.models import DecisionResult, UserFeedbackType


def decide(
    *,
    visits: int,
    conversion_rate: float,
    revenue: float,
    payment_attempted: bool = False,
    payment_success: bool = False,
    feedback: UserFeedbackType | None = None,
) -> DecisionResult:
    """Apply deterministic decision rules with payment + feedback signals."""

    # ── Payment-signal overrides ──────────────────────────────────────
    if payment_success:
        return DecisionResult(
            decision="scale_candidate",
            reason="Payment received – revenue signal confirmed.",
            next_action="Prioritize scaling: increase distribution and expand features.",
            confidence=0.95,
            suggested_next_state="scaled",
            suggested_next_action="scale project",
        )

    if payment_attempted and not payment_success:
        return DecisionResult(
            decision="iterate_pricing",
            reason="Payment was attempted but did not succeed – likely pricing or offer issue.",
            next_action="Review pricing tier, payment flow, and offer clarity.",
            confidence=0.85,
            suggested_next_state="monitoring",
            suggested_next_action="iterate pricing or offer",
        )

    # ── Feedback-signal overrides ─────────────────────────────────────
    if feedback == UserFeedbackType.TOO_EXPENSIVE:
        return DecisionResult(
            decision="iterate_pricing",
            reason="User feedback indicates price is too high.",
            next_action="Reduce pricing or reposition the value proposition.",
            confidence=0.82,
            suggested_next_state="monitoring",
            suggested_next_action="adjust pricing",
        )

    if feedback == UserFeedbackType.NOT_CLEAR:
        return DecisionResult(
            decision="revise_messaging",
            reason="User feedback indicates messaging is unclear.",
            next_action="Improve landing-page copy, CTA, and onboarding flow.",
            confidence=0.80,
            suggested_next_state="monitoring",
            suggested_next_action="improve messaging",
        )

    if feedback == UserFeedbackType.NOT_NEEDED:
        return DecisionResult(
            decision="kill_candidate",
            reason="User feedback indicates the product is not needed.",
            next_action="Downgrade idea score and re-evaluate market fit.",
            confidence=0.78,
            suggested_next_state="killed",
            suggested_next_action="downgrade idea score",
        )

    # ── Combined traffic + payment guard ──────────────────────────────
    if visits >= 100 and payment_attempted and not payment_success:
        return DecisionResult(
            decision="iterate_pricing",
            reason="Sufficient traffic and payment attempted but zero success – iterate once.",
            next_action="Change pricing or offer structure, then measure again.",
            confidence=0.84,
            suggested_next_state="monitoring",
            suggested_next_action="iterate pricing or offer",
        )

    # ── Original conversion-based rules ───────────────────────────────
    if visits >= 200 and conversion_rate < 0.01 and revenue == 0:
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
    if visits >= 200 and conversion_rate < 0.03:
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
