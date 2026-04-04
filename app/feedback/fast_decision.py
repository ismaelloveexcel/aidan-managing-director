"""
fast_decision.py – Enhanced fast decision engine with payment + feedback signals.

Provides a single ``fast_decide`` function that wraps the deterministic
policy and applies additional guards for payment-signal + feedback
iteration logic.

Max 1 iteration is enforced per project to avoid infinite loops.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.feedback.decision_policy import decide
from app.feedback.models import DecisionResult, UserFeedbackType


class FastDecisionInput(BaseModel):
    """Composite input for the fast decision engine."""

    project_id: str
    visits: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    revenue: float = Field(ge=0.0)
    payment_attempted: bool = False
    payment_success: bool = False
    feedback: UserFeedbackType | None = None
    iteration_count: int = Field(default=0, ge=0)


class FastDecisionOutput(BaseModel):
    """Output from the fast decision engine with action + iteration guard."""

    project_id: str
    decision: DecisionResult
    action: str  # scale / kill / iterate / monitor / revise_messaging
    iteration_applied: bool
    max_iterations_reached: bool


_MAX_ITERATIONS = 1


def fast_decide(inp: FastDecisionInput) -> FastDecisionOutput:
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
