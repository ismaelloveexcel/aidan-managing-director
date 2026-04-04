"""
Deterministic input validation for the multi-layer build pipeline.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeterministicValidationResult(BaseModel):
    """Deterministic validation result for a proposed idea payload."""

    valid: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


_REQUIRED_TEXT_FIELDS = (
    "hypothesis",
    "target_user",
    "problem",
    "solution",
    "cta",
    "pricing_hint",
)


def validate_idea_input(idea_input: dict[str, Any]) -> DeterministicValidationResult:
    """Validate an idea input payload using deterministic checks only."""
    issues: list[str] = []
    checks_total = len(_REQUIRED_TEXT_FIELDS) + 2
    checks_passed = 0

    for field in _REQUIRED_TEXT_FIELDS:
        value = idea_input.get(field)
        if isinstance(value, str) and value.strip():
            checks_passed += 1
        else:
            issues.append(f"missing_or_empty_{field}")

    mvp_scope = idea_input.get("mvp_scope")
    if isinstance(mvp_scope, list) and len([x for x in mvp_scope if str(x).strip()]) > 0:
        checks_passed += 1
    else:
        issues.append("missing_or_empty_mvp_scope")

    acceptance = idea_input.get("acceptance_criteria")
    if isinstance(acceptance, list) and len([x for x in acceptance if str(x).strip()]) > 0:
        checks_passed += 1
    else:
        issues.append("missing_or_empty_acceptance_criteria")

    # Penalise scope explosion for one-person operation mode.
    scope_penalty = 0
    if isinstance(mvp_scope, list) and len(mvp_scope) > 8:
        issues.append("scope_too_large")
        scope_penalty = 1

    score = round(max(0.0, min(1.0, (checks_passed - scope_penalty) / checks_total)), 2)
    return DeterministicValidationResult(valid=len(issues) == 0, score=score, issues=issues)
