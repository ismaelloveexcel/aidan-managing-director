"""
Validation helpers for BuildBrief contract enforcement.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.factory.models import BuildBrief, BuildBriefValidationResult


def validate_build_brief(brief: BuildBrief) -> BuildBriefValidationResult:
    """Validate a BuildBrief instance and return structured validation output."""
    errors: list[str] = []

    # Semantic guards beyond field-level Pydantic checks.
    if len(brief.mvp_scope) > 25:
        errors.append("mvp_scope has too many items (max 25 for MVP discipline).")
    if len(brief.acceptance_criteria) > 25:
        errors.append(
            "acceptance_criteria has too many items (max 25 for MVP discipline).",
        )

    if errors:
        return BuildBriefValidationResult(valid=False, errors=errors)

    return BuildBriefValidationResult(
        valid=True,
        errors=[],
        brief_hash=brief.brief_hash(),
        idempotency_key=brief.idempotency_key(),
    )


def validate_build_brief_payload(payload: dict[str, Any]) -> BuildBriefValidationResult:
    """Parse and validate a raw BuildBrief payload."""
    try:
        brief = BuildBrief(**payload)
    except ValidationError as exc:
        return BuildBriefValidationResult(
            valid=False,
            errors=[err["msg"] for err in exc.errors()],
        )
    return validate_build_brief(brief)
