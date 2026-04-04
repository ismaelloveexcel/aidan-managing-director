"""
approvals.py – Routes for human-in-the-loop approval workflows.

Handles queuing, reviewing, and resolving approval requests before
AI-DAN dispatches high-impact commands.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.telemetry import emit_event
from app.core.dependencies import get_governance_service
from app.governance.models import GovernanceReviewRequest
from app.planning.approval_gate import ApprovalGate

router = APIRouter()

_approval_gate = ApprovalGate()
_governance = get_governance_service()


class ApprovalRequest(BaseModel):
    """Payload representing an action pending approval."""

    action_id: str | None = None
    action_type: str
    payload: dict[str, Any]


class ApprovalDecision(BaseModel):
    """Decision payload for approving or rejecting an action."""

    action_id: str
    approved: bool
    reason: str | None = None


class ApprovalResponse(BaseModel):
    """Status response after processing an approval decision."""

    action_id: str
    status: str
    reason: str | None = None


class GovernanceReviewResponse(BaseModel):
    """Policy review response without mutating approval queues."""

    action: str
    classification: str
    approved: bool
    requires_human: bool
    reason: str
    policy_tags: list[str]


@router.post("/review", response_model=GovernanceReviewResponse)
async def review_action_policy(request: ApprovalRequest) -> GovernanceReviewResponse:
    """Run governance policy review for an action without queue mutation."""
    decision = _governance.review(
        GovernanceReviewRequest(action=request.action_type, parameters=request.payload),
    )
    return GovernanceReviewResponse(
        action=decision.action,
        classification=decision.classification.value,
        approved=decision.approved,
        requires_human=decision.requires_human,
        reason=decision.reason,
        policy_tags=decision.policy_tags,
    )


@router.post("/", response_model=ApprovalResponse)
async def request_approval(request: ApprovalRequest) -> ApprovalResponse:
    """Queue an action for approval, or auto-approve when not required."""
    command = {
        "action": request.action_type,
        "parameters": request.payload,
        "external_action_id": request.action_id,
    }
    if not _approval_gate.requires_approval(command):
        resolved_id = request.action_id or "auto-approved"
        _governance.request_approval(
            action_id=resolved_id,
            action_type=request.action_type,
            payload=request.payload,
            requires_approval=False,
        )
        _governance.decide_approval(
            action_id=resolved_id,
            approved=True,
            reason="Action does not require approval under current policy.",
        )
        emit_event(
            "approval_auto_approved",
            {
                "action_id": resolved_id,
                "action_type": request.action_type,
            },
        )
        return ApprovalResponse(
            action_id=resolved_id,
            status="approved",
            reason="Action does not require approval under current policy.",
        )

    action_id = _approval_gate.submit(command)
    _governance.request_approval(
        action_id=action_id,
        action_type=request.action_type,
        payload=request.payload,
        requires_approval=True,
    )
    emit_event(
        "approval_requested",
        {
            "action_id": action_id,
            "action_type": request.action_type,
        },
    )
    return ApprovalResponse(action_id=action_id, status="pending")


@router.post("/decide", response_model=ApprovalResponse)
async def decide_approval(decision: ApprovalDecision) -> ApprovalResponse:
    """Process an approval decision for a queued action."""
    governance_record = _governance.decide_approval(
        action_id=decision.action_id,
        approved=decision.approved,
        reason=decision.reason,
    )
    if governance_record is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    try:
        resolved = _approval_gate.resolve(
            action_id=decision.action_id,
            approved=decision.approved,
            reason=decision.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    emit_event(
        "approval_resolved",
        {
            "action_id": decision.action_id,
            "status": resolved["status"],
        },
    )
    return ApprovalResponse(
        action_id=resolved["action_id"],
        status=resolved["status"],
        reason=governance_record.reason or resolved.get("reason"),
    )


@router.get("/", response_model=list[ApprovalResponse])
async def list_pending_approvals() -> list[ApprovalResponse]:
    """Return all actions currently awaiting approval."""
    pending = _approval_gate.list_pending()
    return [
        ApprovalResponse(
            action_id=record["action_id"],
            status=record["status"],
            reason=record.get("reason"),
        )
        for record in pending
    ]
