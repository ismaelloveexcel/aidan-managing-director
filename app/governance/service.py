"""
governance/service.py - policy-driven approval and command governance.
"""

from __future__ import annotations

from typing import Any

from app.core.telemetry import emit_event
from app.governance.models import (
    ApprovalDecisionRecord,
    ApprovalRecord,
    ApprovalStatus,
    CommandSafetyClassification,
    GovernanceDecision,
    GovernanceReviewRequest,
    utcnow_iso,
)
from app.planning.approval_gate import HIGH_IMPACT_ACTIONS

_BLOCKED_ACTIONS = frozenset({"delete_repo", "modify_billing"})


class GovernanceService:
    """Deterministic governance layer for command safety decisions."""

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRecord] = {}
        self._decision_log: list[ApprovalDecisionRecord] = []

    def classify_command(self, action: str, parameters: dict[str, Any]) -> CommandSafetyClassification:
        """Classify command risk based on action and payload hints."""
        lowered_action = action.strip().lower()
        if lowered_action in _BLOCKED_ACTIONS:
            return CommandSafetyClassification.BLOCKED
        if lowered_action in HIGH_IMPACT_ACTIONS:
            return CommandSafetyClassification.REQUIRES_APPROVAL
        if parameters.get("environment") == "production":
            return CommandSafetyClassification.REQUIRES_APPROVAL
        return CommandSafetyClassification.SAFE

    def review(self, request: GovernanceReviewRequest) -> GovernanceDecision:
        """Produce deterministic governance decision for a command request."""
        classification = self.classify_command(request.action, request.parameters)

        if classification == CommandSafetyClassification.BLOCKED:
            decision = GovernanceDecision(
                action=request.action,
                classification=classification,
                approved=False,
                requires_human=False,
                reason="Command action is explicitly blocked by policy.",
                policy_tags=["blocked_action"],
            )
        elif classification == CommandSafetyClassification.REQUIRES_APPROVAL:
            decision = GovernanceDecision(
                action=request.action,
                classification=classification,
                approved=False,
                requires_human=True,
                reason="Command requires explicit human approval.",
                policy_tags=["human_gate_required"],
            )
        else:
            decision = GovernanceDecision(
                action=request.action,
                classification=classification,
                approved=True,
                requires_human=False,
                reason="Command is within deterministic safe-execution policy.",
                policy_tags=["auto_approved"],
            )

        emit_event(
            "governance_reviewed",
            {
                "action": request.action,
                "classification": decision.classification.value,
                "approved": decision.approved,
                "requires_human": decision.requires_human,
            },
        )
        return decision

    def request_approval(
        self,
        *,
        action_id: str,
        action_type: str,
        payload: dict[str, Any],
        requires_approval: bool,
    ) -> ApprovalRecord:
        """Create or refresh an approval record for an action."""
        existing = self._approvals.get(action_id)
        if existing is not None:
            return existing

        status = ApprovalStatus.PENDING if requires_approval else ApprovalStatus.APPROVED
        record = ApprovalRecord(
            action_id=action_id,
            action_type=action_type,
            payload=payload,
            status=status,
            requires_approval=requires_approval,
            reason=None if requires_approval else "Auto-approved by policy.",
        )
        self._approvals[action_id] = record
        return record

    def decide_approval(
        self,
        *,
        action_id: str,
        approved: bool,
        reason: str | None,
        actor: str = "human",
    ) -> ApprovalDecisionRecord | None:
        """Apply human decision to an approval record."""
        record = self._approvals.get(action_id)
        if record is None:
            return None
        record.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        record.reason = reason
        record.resolved_at = utcnow_iso()

        decision = ApprovalDecisionRecord(
            action_id=action_id,
            decision=record.status,
            reason=reason,
            actor=actor,
            metadata={"action_type": record.action_type},
        )
        self._decision_log.append(decision)
        emit_event(
            "governance_approval_decided",
            {
                "action_id": action_id,
                "decision": decision.decision.value,
                "actor": actor,
            },
        )
        return decision

    def list_pending_approvals(self) -> list[ApprovalRecord]:
        """Return all approvals still awaiting human decision."""
        return [
            record
            for record in self._approvals.values()
            if record.status == ApprovalStatus.PENDING
        ]
