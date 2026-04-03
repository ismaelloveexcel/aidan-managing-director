"""
Guardian agent for feasibility and scope risk checks.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GuardianReviewResult(BaseModel):
    """Structured output from guardian review."""

    decision: Literal["APPROVE", "FLAG", "BLOCK"]
    reason: str
    risk_flags: list[str] = Field(default_factory=list)


class GuardianAgent:
    """Deterministic guardrail checks before factory execution."""

    def review(
        self,
        *,
        idea_input: dict[str, Any],
        validation_score: float,
        monetization_model: str,
    ) -> GuardianReviewResult:
        """Run feasibility, overlap, monetization, and scope checks."""
        risk_flags: list[str] = []

        mvp_scope = idea_input.get("mvp_scope", [])
        idea_title = str(idea_input.get("title", "")).strip().lower()
        pricing_hint = str(idea_input.get("pricing_hint", "")).strip()

        if validation_score < 0.45:
            risk_flags.append("low_validation_score")

        # Placeholder overlap check (deterministic and transparent).
        overlap_tokens = ("clone", "copycat", "me-too")
        if any(token in idea_title for token in overlap_tokens):
            risk_flags.append("possible_duplicate_overlap")

        if not monetization_model.strip() and not pricing_hint:
            risk_flags.append("missing_monetization_logic")

        if not isinstance(mvp_scope, list) or len(mvp_scope) == 0:
            risk_flags.append("missing_scope")
        elif len(mvp_scope) > 8:
            risk_flags.append("scope_too_large")
        elif len(mvp_scope) > 5:
            risk_flags.append("scope_risk_medium")

        if "scope_too_large" in risk_flags or "missing_scope" in risk_flags:
            return GuardianReviewResult(
                decision="BLOCK",
                reason="Scope exceeds safe MVP boundaries for one-person execution.",
                risk_flags=risk_flags,
            )

        if risk_flags:
            return GuardianReviewResult(
                decision="FLAG",
                reason="Project can proceed only after addressing flagged risks.",
                risk_flags=risk_flags,
            )

        return GuardianReviewResult(
            decision="APPROVE",
            reason="Project passes guardian checks.",
            risk_flags=[],
        )
