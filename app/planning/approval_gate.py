"""
approval_gate.py – Human-in-the-loop gate for high-impact commands.

Intercepts commands that require human review before execution and
manages the approval lifecycle (pending → approved/rejected).
"""

from typing import Any


class ApprovalGate:
    """
    Manages the approval workflow for commands flagged as high-impact.

    Business logic to be implemented in a future iteration.
    """

    def requires_approval(self, command: dict[str, Any]) -> bool:
        """
        Determine whether a command must pass through the approval gate.

        Args:
            command: The command to inspect.

        Returns:
            True if human approval is required, False otherwise.
        """
        raise NotImplementedError

    def submit(self, command: dict[str, Any]) -> str:
        """
        Submit a command for human approval and return a tracking ID.

        Args:
            command: The command to submit for review.

        Returns:
            A unique action ID for tracking the approval request.
        """
        raise NotImplementedError

    def resolve(self, action_id: str, approved: bool, reason: str | None = None) -> dict[str, Any]:
        """
        Resolve an approval request as approved or rejected.

        Args:
            action_id: Unique identifier of the approval request.
            approved: Whether the action is approved.
            reason: Optional human-supplied rationale for the decision.

        Returns:
            Updated approval record reflecting the decision.
        """
        raise NotImplementedError
