"""
approvals.py – Routes for human-in-the-loop approval workflows.

Handles queuing, reviewing, and resolving approval requests before
AI-DAN dispatches high-impact commands.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.telemetry import emit_event
from app.planning.approval_gate import ApprovalGate

router = APIRouter()

_approval_gate = ApprovalGate()


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
        reason=resolved.get("reason"),
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
