"""
Business validation gate – enforces REAL validation before any idea proceeds.

Rules:
- NO demand evidence → REJECT
- NO monetization proof → REJECT  
- HIGH saturation + weak differentiation → REJECT
- Must pass ALL gates to proceed
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GateDecision(str, Enum):
    """Possible gate outcomes."""

    PASS = "pass"
    REJECT = "reject"


class ValidationResult(BaseModel):
    """Result of business validation gate."""

    decision: GateDecision
    demand_valid: bool = False
    monetization_valid: bool = False
    saturation_ok: bool = False
    differentiation_ok: bool = False
    reasons: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Demand evidence keywords – idea must reference real user need
# ---------------------------------------------------------------------------
_DEMAND_SIGNALS = frozenset({
    "users", "customers", "demand", "need", "pain", "problem",
    "struggle", "frustration", "market", "audience", "segment",
    "waitlist", "requests", "survey", "feedback", "interviews",
    "validation", "traction", "adoption", "growth", "retention",
    "recurring", "repeat", "loyal", "engagement",
})

# ---------------------------------------------------------------------------
# Monetization proof keywords
# ---------------------------------------------------------------------------
_MONETIZATION_SIGNALS = frozenset({
    "subscription", "saas", "pricing", "revenue", "payment",
    "freemium", "premium", "tier", "plan", "charge", "billing",
    "monetize", "monetization", "commission", "fee", "license",
    "marketplace", "ads", "advertising", "sponsorship", "affiliate",
    "pay", "paid", "income", "profit", "margin", "arpu", "ltv",
    "mrr", "arr", "transaction", "checkout", "purchase",
})

# ---------------------------------------------------------------------------
# High-saturation keywords
# ---------------------------------------------------------------------------
_SATURATION_SIGNALS = frozenset({
    "crowded", "saturated", "many competitors", "red ocean",
    "commodity", "dominated", "established players",
})


# Minimum length for differentiation text to be considered meaningful.
_MIN_DIFFERENTIATION_LENGTH = 10


def _token_set(text: str) -> set[str]:
    """Return lowercase word tokens from text."""
    return {w.strip(".,;:!?()[]{}\"'") for w in text.lower().split()}


def _text_contains_any(text: str, signals: frozenset[str]) -> bool:
    """Check if text contains any signal keywords."""
    tokens = _token_set(text)
    lower_text = text.lower()
    for signal in signals:
        if " " in signal:
            if signal in lower_text:
                return True
        elif signal in tokens:
            return True
    return False


def validate_business_gate(
    *,
    idea_text: str,
    problem: str = "",
    target_user: str = "",
    monetization_model: str = "",
    competition_level: str = "",
    differentiation: str = "",
    extra: dict[str, Any] | None = None,
) -> ValidationResult:
    """Run the full business validation gate.

    Args:
        idea_text: The full idea description.
        problem: Explicit problem statement.
        target_user: Target user/customer description.
        monetization_model: Proposed monetization approach.
        competition_level: Description of competition (low/medium/high).
        differentiation: What makes this idea unique.
        extra: Optional additional context.

    Returns:
        ValidationResult with pass/reject decision and reasons.
    """
    combined_text = " ".join(filter(None, [
        idea_text, problem, target_user, monetization_model,
        competition_level, differentiation,
    ]))

    reasons: list[str] = []
    blocking: list[str] = []

    # --- Gate 1: Demand evidence ---
    demand_valid = bool(problem.strip()) and (
        bool(target_user.strip())
        or _text_contains_any(combined_text, _DEMAND_SIGNALS)
    )
    if demand_valid:
        reasons.append("Demand evidence present: problem and target user identified.")
    else:
        blocking.append("NO demand evidence: missing problem statement or target user.")

    # --- Gate 2: Monetization proof ---
    monetization_valid = bool(monetization_model.strip()) or _text_contains_any(
        combined_text, _MONETIZATION_SIGNALS,
    )
    if monetization_valid:
        reasons.append("Monetization path identified.")
    else:
        blocking.append("NO monetization proof: no pricing or revenue model specified.")

    # --- Gate 3: Saturation check ---
    is_saturated = (
        competition_level.lower() in {"high", "very high", "extreme"}
        or _text_contains_any(combined_text, _SATURATION_SIGNALS)
    )

    # --- Gate 4: Differentiation check ---
    has_differentiation = bool(differentiation.strip()) and len(differentiation.strip()) > _MIN_DIFFERENTIATION_LENGTH

    saturation_ok = True
    differentiation_ok = True

    if is_saturated and not has_differentiation:
        saturation_ok = False
        differentiation_ok = False
        blocking.append(
            "HIGH saturation with WEAK differentiation: "
            "market is crowded and no clear unique advantage stated."
        )
    elif is_saturated and has_differentiation:
        reasons.append("Saturated market but differentiation is present.")
    else:
        reasons.append("Market saturation is acceptable.")

    # --- Final decision ---
    decision = GateDecision.PASS if not blocking else GateDecision.REJECT

    return ValidationResult(
        decision=decision,
        demand_valid=demand_valid,
        monetization_valid=monetization_valid,
        saturation_ok=saturation_ok,
        differentiation_ok=differentiation_ok,
        reasons=reasons,
        blocking_reasons=blocking,
    )
