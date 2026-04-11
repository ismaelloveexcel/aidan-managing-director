"""
revenue.py – Routes for revenue intelligence: auto-learning, fast decisions,
and business output snapshots.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.dependencies import get_auto_learner, get_feedback_service, get_memory_store
from app.feedback.fast_decision import FastDecisionInput, FastDecisionOutput, fast_decide_with_signals
from app.memory.auto_learner import AutoLearnerReport
from app.planning.business_output import RevenueBusinessOutput, build_revenue_business_output

router = APIRouter()

_auto_learner = get_auto_learner()
_feedback = get_feedback_service()
_memory = get_memory_store()


# ---------------------------------------------------------------------------
# Auto-learning
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/learning-report", response_model=AutoLearnerReport)
async def get_learning_report(project_id: str) -> AutoLearnerReport:
    """Return the auto-learner analysis report for a project."""
    return _auto_learner.analyse(project_id)


# ---------------------------------------------------------------------------
# Fast decision engine
# ---------------------------------------------------------------------------


@router.post("/fast-decision", response_model=FastDecisionOutput)
async def run_fast_decision(payload: FastDecisionInput) -> FastDecisionOutput:
    """Run the fast decision engine with payment + feedback signals."""
    return fast_decide_with_signals(payload)


# ---------------------------------------------------------------------------
# Business output
# ---------------------------------------------------------------------------


class BusinessOutputRequest(BaseModel):
    """Optional overrides when generating a business output snapshot."""

    payment_link: str | None = None
    pricing_strategy: str = "default"


@router.post("/projects/{project_id}/business-output", response_model=RevenueBusinessOutput)
async def generate_business_output(project_id: str, payload: BusinessOutputRequest) -> RevenueBusinessOutput:
    """Generate a structured business output snapshot for a project."""
    decision = _feedback.get_project_decision(project_id)

    # Gather feedback counts from memory signals.
    signals = _memory.get_project_signals(project_id, limit=10_000)
    feedback_counts: dict[str, int] = {}
    for sig in signals:
        feedback_counts[sig.signal_type] = feedback_counts.get(sig.signal_type, 0) + 1

    # Determine conversion status from the decision.
    conversion_status = "unknown"
    if decision is not None:
        status_map = {
            "scale_candidate": "converting",
            "kill_candidate": "not_converting",
            "revise_candidate": "underperforming",
            "iterate_pricing": "blocked_by_pricing",
            "revise_messaging": "blocked_by_messaging",
            "monitor": "insufficient_data",
        }
        conversion_status = status_map.get(decision.decision, "unknown")

    return build_revenue_business_output(
        project_id=project_id,
        payment_link=payload.payment_link,
        pricing_strategy=payload.pricing_strategy,
        feedback_counts=feedback_counts,
        conversion_status=conversion_status,
        latest_decision=decision,
    )
