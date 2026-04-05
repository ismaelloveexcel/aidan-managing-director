"""
Fast decision engine — combines strict iteration-limited rules with
payment + feedback signal awareness.

Original engine (``fast_decide``):
- visits >= 100 AND conversions = 0 -> terminate
- visits >= 100 AND interest only (signups > 0, revenue = 0) -> ITERATE ONCE
- revenue detected -> SCALE
- no traffic -> change distribution ONCE -> if still none -> terminate
- MAX 1 iteration per project; NO infinite loops.

Enhanced engine (``fast_decide_with_signals``):
- Wraps the deterministic decision policy with payment + feedback
  awareness and a max-1-iteration guard.
"""

from __future__ import annotations

import threading
from typing import Literal

from pydantic import BaseModel, Field

from app.feedback.decision_policy import decide
from app.feedback.models import DecisionResult, UserFeedbackType


# ======================================================================
# Original fast decision engine (traffic + revenue based)
# ======================================================================


class FastDecision(BaseModel):
    """Output of the fast decision engine."""

    action: Literal["KILL", "ITERATE", "SCALE", "CHANGE_DISTRIBUTION", "MONITOR"]
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    iteration_count: int = 0
    max_iterations: int = 1
    can_iterate: bool = True


# Project-level iteration tracking (in-memory; replaced by DB/SQLite in Phase 2).
# Protected by a lock for thread-safety across concurrent requests.
_iteration_tracker: dict[str, int] = {}
_tracker_lock = threading.Lock()


def reset_tracker() -> None:
    """Clear iteration tracking state (for testing)."""
    with _tracker_lock:
        _iteration_tracker.clear()


def fast_decide(
    *,
    project_id: str,
    visits: int,
    signups: int,
    revenue: float,
    has_distribution: bool = True,
    distribution_changed: bool = False,
) -> FastDecision:
    """Apply strict fast-decision rules with iteration limits.

    Args:
        project_id: Unique project identifier.
        visits: Total page visits.
        signups: Total sign-ups or leads.
        revenue: Total revenue generated.
        has_distribution: Whether any distribution channel is active.
        distribution_changed: Whether distribution was already changed once.

    Returns:
        A FastDecision with the action, reason, and iteration metadata.
    """
    with _tracker_lock:
        iterations = _iteration_tracker.get(project_id, 0)
        can_iterate = iterations < 1

        # Rule 1: Revenue detected -> SCALE immediately.
        if revenue > 0:
            return FastDecision(
                action="SCALE",
                reason="Revenue detected; scale distribution and feature expansion.",
                confidence=0.92,
                iteration_count=iterations,
                can_iterate=can_iterate,
            )

        # Rule 2: Sufficient traffic but zero conversions -> terminate.
        if visits >= 100 and signups == 0 and revenue == 0:
            return FastDecision(
                action="KILL",
                reason="100+ visits with zero conversions; project is not viable.",
                confidence=0.90,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Rule 3: Traffic with interest (signups) but no revenue -> ITERATE once.
        if visits >= 100 and signups > 0 and revenue == 0:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="ITERATE",
                    reason="Interest detected but no revenue; iterate messaging/CTA once.",
                    confidence=0.82,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Already iterated once with no revenue; project terminated.",
                confidence=0.88,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Rule 4: No traffic -> change distribution once, then terminate.
        # All CHANGE_DISTRIBUTION paths consume the single allowed iteration.
        if visits < 10 and not has_distribution:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="CHANGE_DISTRIBUTION",
                    reason="No distribution channel active; activate one before deciding.",
                    confidence=0.75,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Distribution was already changed once with no traffic; project terminated.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        if visits < 10 and distribution_changed:
            return FastDecision(
                action="KILL",
                reason="Distribution changed but still no traffic; project terminated.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        if visits < 10 and has_distribution:
            if can_iterate:
                _iteration_tracker[project_id] = iterations + 1
                return FastDecision(
                    action="CHANGE_DISTRIBUTION",
                    reason="No traffic despite active distribution; change channel once.",
                    confidence=0.78,
                    iteration_count=iterations + 1,
                    can_iterate=False,
                )
            return FastDecision(
                action="KILL",
                reason="Already changed distribution once with no traffic; project terminated.",
                confidence=0.85,
                iteration_count=iterations,
                can_iterate=False,
            )

        # Default: continue monitoring.
        return FastDecision(
            action="MONITOR",
            reason="Insufficient signal for decisive action; continue collecting data.",
            confidence=0.60,
            iteration_count=iterations,
            can_iterate=can_iterate,
        )


# ======================================================================
# Enhanced fast decision engine (payment + feedback signal aware)
# ======================================================================


class FastDecisionInput(BaseModel):
    """Composite input for the enhanced fast decision engine."""

    project_id: str
    visits: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    revenue: float = Field(ge=0.0)
    payment_attempted: bool = False
    payment_success: bool = False
    feedback: UserFeedbackType | None = None
    iteration_count: int = Field(default=0, ge=0)


class FastDecisionOutput(BaseModel):
    """Output from the enhanced fast decision engine with action + iteration guard."""

    project_id: str
    decision: DecisionResult
    action: str  # scale / kill / iterate / monitor / revise_messaging
    iteration_applied: bool
    max_iterations_reached: bool


_MAX_ITERATIONS = 1


def fast_decide_with_signals(inp: FastDecisionInput) -> FastDecisionOutput:
    """Run the enhanced fast decision engine (max 1 iteration)."""
    max_reached = inp.iteration_count >= _MAX_ITERATIONS

    decision = decide(
        visits=inp.visits,
        conversion_rate=inp.conversion_rate,
        revenue=inp.revenue,
        payment_attempted=inp.payment_attempted,
        payment_success=inp.payment_success,
        feedback=inp.feedback,
    )

    # Map policy decision to a simplified action label.
    action = _map_action(decision.decision, max_reached=max_reached)

    iteration_applied = action == "iterate" and not max_reached

    return FastDecisionOutput(
        project_id=inp.project_id,
        decision=decision,
        action=action,
        iteration_applied=iteration_applied,
        max_iterations_reached=max_reached,
    )


def _map_action(decision: str, *, max_reached: bool) -> str:
    """Map a policy decision string to a fast-decision action label."""
    if decision == "scale_candidate":
        return "scale"
    if decision == "kill_candidate":
        return "kill"
    if decision in ("iterate_pricing", "revise_candidate"):
        if max_reached:
            return "kill"
        return "iterate"
    if decision == "revise_messaging":
        if max_reached:
            return "monitor"
        return "revise_messaging"
    return "monitor"
