"""
Models for governance approvals and command safety decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ApprovalStatus(str, Enum):
    """Governance approval lifecycle status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommandSafetyClassification(str, Enum):
    """Deterministic classification for command safety policy."""

    SAFE = "safe"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


class GovernanceReviewRequest(BaseModel):
    """Request payload used by governance policy review."""

    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GovernanceDecision(BaseModel):
    """Deterministic governance policy output for a command."""

    action: str
    classification: CommandSafetyClassification
    approved: bool
    requires_human: bool
    reason: str
    policy_tags: list[str] = Field(default_factory=list)


class ApprovalRecord(BaseModel):
    """Structured governance approval record."""

    action_id: str
    action_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    requires_approval: bool = True
    reason: str | None = None
    requested_at: str = Field(default_factory=utcnow_iso)
    resolved_at: str | None = None


class ApprovalDecisionRecord(BaseModel):
    """Structured decision log record for approved/rejected actions."""

    action_id: str
    decision: ApprovalStatus
    reason: str | None = None
    actor: str = "system"
    timestamp: str = Field(default_factory=utcnow_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)
