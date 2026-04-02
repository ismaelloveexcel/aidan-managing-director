"""
approvals.py – Routes for human-in-the-loop approval workflows.

Handles queuing, reviewing, and resolving approval requests before
AI-DAN dispatches high-impact commands.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ApprovalRequest(BaseModel):
    """Payload representing an action pending approval."""

    action_id: str
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


@router.post("/", response_model=ApprovalResponse)
async def request_approval(request: ApprovalRequest) -> ApprovalResponse:
    """
    Queue an action for human approval review.

    Business logic to be implemented in a future iteration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/decide", response_model=ApprovalResponse)
async def decide_approval(decision: ApprovalDecision) -> ApprovalResponse:
    """
    Process an approval or rejection decision for a queued action.

    Business logic to be implemented in a future iteration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/", response_model=list[ApprovalResponse])
async def list_pending_approvals() -> list[ApprovalResponse]:
    """
    Return all actions currently awaiting approval.

    Business logic to be implemented in a future iteration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
