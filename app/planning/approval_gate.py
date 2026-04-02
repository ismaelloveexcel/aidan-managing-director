"""
approval_gate.py – Human-in-the-loop gate for high-impact commands.

Determines which commands require human review before execution and
manages the approval lifecycle (pending → approved / rejected).
No execution logic lives here – only approval decisions and state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration – actions that always require human approval
# ---------------------------------------------------------------------------

HIGH_IMPACT_ACTIONS: frozenset[str] = frozenset(
    {
        "deploy",
        "delete_repo",
        "modify_billing",
        "launch_marketing",
    },
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ApprovalRecord(BaseModel):
    """Tracks the lifecycle of a single approval request."""

    action_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    command: dict[str, Any]
    status: str = "pending"  # pending | approved | rejected
    reason: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    resolved_at: str | None = None


# ---------------------------------------------------------------------------
# Public API – standalone function
# ---------------------------------------------------------------------------


def requires_approval(command: dict[str, Any]) -> bool:
    """Determine whether a command must pass through the approval gate.

    A command requires approval when its ``action`` field matches a
    known high-impact action **or** when it is explicitly marked with
    ``"requires_approval": True``.

    Args:
        command: The command dictionary to inspect.  Must contain an
                 ``action`` key.

    Returns:
        True if human approval is required, False otherwise.
    """
    if command.get("requires_approval") is True:
        return True
    return command.get("action", "") in HIGH_IMPACT_ACTIONS


# ---------------------------------------------------------------------------
# Class-based interface (kept for backward compatibility with routes)
# ---------------------------------------------------------------------------


class ApprovalGate:
    """Manages the approval workflow for commands flagged as high-impact.

    Maintains an **in-memory** registry of approval records.  A
    persistent backend can be swapped in later without changing the
    public interface.
    """

    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRecord] = {}

    def requires_approval(self, command: dict[str, Any]) -> bool:
        """Proxy to the module-level :func:`requires_approval`."""
        return requires_approval(command)

    def submit(self, command: dict[str, Any]) -> str:
        """Submit a command for human approval and return a tracking ID.

        Args:
            command: The command to submit for review.

        Returns:
            A unique action ID for tracking the approval request.
        """
        record = ApprovalRecord(command=command)
        self._pending[record.action_id] = record
        return record.action_id

    def resolve(
        self,
        action_id: str,
        approved: bool,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Resolve an approval request as approved or rejected.

        Args:
            action_id: Unique identifier of the approval request.
            approved: Whether the action is approved.
            reason: Optional human-supplied rationale for the decision.

        Returns:
            Updated approval record reflecting the decision.

        Raises:
            KeyError: If no pending record matches *action_id*.
        """
        if action_id not in self._pending:
            raise KeyError(f"No pending approval found for action_id={action_id!r}")

        record = self._pending[action_id]
        record.status = "approved" if approved else "rejected"
        record.reason = reason
        record.resolved_at = datetime.now(timezone.utc).isoformat()
        return record.model_dump()

    def list_pending(self) -> list[dict[str, Any]]:
        """Return all commands currently awaiting approval.

        Returns:
            A list of serialised :class:`ApprovalRecord` dictionaries
            whose status is ``"pending"``.
        """
        return [
            record.model_dump()
            for record in self._pending.values()
            if record.status == "pending"
        ]
