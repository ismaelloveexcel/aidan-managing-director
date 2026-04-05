"""
Revenue scoring engine – 0-10 scoring across 5 mandatory dimensions.

Each dimension scored 0-2:
1. Demand (0-2)
2. Monetization (0-2)
3. Saturation (0-2, reverse: lower saturation = higher score)
4. Complexity (0-2, reverse: lower complexity = higher score)
5. Speed to revenue (0-2)

Total: 0-10
- <6 → REJECT
- 6-7 → HOLD
- >=8 → APPROVE
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScoringDecision(str, Enum):
    """Score-based decisions."""

    REJECT = "reject"
    HOLD = "hold"
    APPROVE = "approve"


class DimensionScore(BaseModel):
    """Score for a single dimension."""

    name: str
    score: float = Field(ge=0.0, le=2.0)
    reason: str = ""


class RevenueScore(BaseModel):
    """Complete revenue scoring result."""

    total_score: float = Field(ge=0.0, le=10.0)
    decision: ScoringDecision
    dimensions: list[DimensionScore] = Field(default_factory=list)
    breakdown: dict[str, float] = Field(default_factory=dict)
    decision_reason: str = ""


# ---------------------------------------------------------------------------
# Keyword-based signal detectors
# ---------------------------------------------------------------------------

_DEMAND_STRONG = frozenset({
    "waitlist", "pre-orders", "survey", "interviews", "traction",
    "growing", "recurring", "retention", "loyal", "engagement",
    "validated", "demand", "customers", "users",
})
_DEMAND_MODERATE = frozenset({
    "need", "pain", "problem", "frustration", "audience", "market",
    "segment", "feedback", "requests",
})

_MONETIZATION_STRONG = frozenset({
    "subscription", "saas", "recurring", "mrr", "arr", "pricing",
    "revenue", "payment", "billing", "checkout", "purchase",
    "freemium", "premium", "tier", "plan",
})
_MONETIZATION_MODERATE = frozenset({
    "monetize", "commission", "fee", "ads", "affiliate",
    "marketplace", "sponsorship", "license",
})

_COMPLEXITY_HIGH = frozenset({
    "complex", "infrastructure", "blockchain", "hardware",
    "regulatory", "compliance", "enterprise", "integration",
    "machine learning", "deep learning", "neural",
})
_COMPLEXITY_LOW = frozenset({
    "simple", "mvp", "landing page", "no-code", "template",
    "wrapper", "api", "lightweight", "minimal",
})

_SPEED_FAST = frozenset({
    "quick", "fast", "rapid", "days", "week", "weekend",
    "mvp", "template", "no-code", "simple", "launch fast",
})
_SPEED_SLOW = frozenset({
    "months", "years", "long-term", "complex", "infrastructure",
    "enterprise", "regulatory",
})


def _token_set(text: str) -> set[str]:
    """Return lowercase word tokens from text."""
    return {w.strip(".,;:!?()[]{}\"'") for w in text.lower().split()}


def _signal_strength(text: str, strong: frozenset[str], moderate: frozenset[str]) -> float:
    """Score 0-2 based on keyword signal strength."""
    tokens = _token_set(text)
    lower = text.lower()

    strong_hits = sum(
        1 for s in strong
        if (s in lower if " " in s else s in tokens)
    )
    moderate_hits = sum(
        1 for s in moderate
        if (s in lower if " " in s else s in tokens)
    )

    if strong_hits >= 2:
        return 2.0
    if strong_hits >= 1:
        return 1.5
    if moderate_hits >= 2:
        return 1.0
    if moderate_hits >= 1:
        return 0.5
    return 0.0


def _score_demand(text: str) -> DimensionScore:
    """Score demand evidence 0-2."""
    score = _signal_strength(text, _DEMAND_STRONG, _DEMAND_MODERATE)
    if score >= 1.5:
        reason = "Strong demand signals detected."
    elif score >= 1.0:
        reason = "Moderate demand evidence present."
    elif score > 0:
        reason = "Weak demand signals."
    else:
        reason = "No demand evidence found."
    return DimensionScore(name="demand", score=score, reason=reason)


def _score_monetization(text: str) -> DimensionScore:
    """Score monetization clarity 0-2."""
    score = _signal_strength(text, _MONETIZATION_STRONG, _MONETIZATION_MODERATE)
    if score >= 1.5:
        reason = "Clear monetization path with strong signals."
    elif score >= 1.0:
        reason = "Monetization model present."
    elif score > 0:
        reason = "Weak monetization signals."
    else:
        reason = "No monetization model detected."
    return DimensionScore(name="monetization", score=score, reason=reason)


def _score_saturation(text: str, competition_level: str) -> DimensionScore:
    """Score saturation 0-2 (REVERSE: low saturation = high score)."""
    lower = competition_level.lower().strip()
    if lower in {"none", "very low", "low"}:
        score = 2.0
        reason = "Low market saturation — clear opportunity."
    elif lower in {"medium", "moderate"}:
        score = 1.0
        reason = "Moderate competition — differentiation needed."
    elif lower in {"high", "very high", "extreme"}:
        score = 0.0
        reason = "High saturation — strong differentiation required."
    else:
        # Infer from text
        sat_signals = {"crowded", "saturated", "red ocean", "commodity", "dominated"}
        tokens = _token_set(text)
        hits = sum(1 for s in sat_signals if s in tokens or s in text.lower())
        if hits >= 2:
            score = 0.0
            reason = "Text suggests high market saturation."
        elif hits == 1:
            score = 1.0
            reason = "Some saturation signals detected."
        else:
            score = 1.5
            reason = "No significant saturation signals."
    return DimensionScore(name="saturation", score=score, reason=reason)


def _score_complexity(text: str, difficulty: str) -> DimensionScore:
    """Score complexity 0-2 (REVERSE: low complexity = high score)."""
    lower = difficulty.lower().strip()
    if lower in {"easy", "simple", "low"}:
        score = 2.0
        reason = "Low complexity — quick to build."
    elif lower in {"medium", "moderate"}:
        score = 1.0
        reason = "Moderate complexity."
    elif lower in {"hard", "high", "complex", "very high"}:
        score = 0.0
        reason = "High complexity — significant build effort."
    else:
        low_hits = sum(
            1 for s in _COMPLEXITY_LOW
            if (s in text.lower() if " " in s else s in _token_set(text))
        )
        high_hits = sum(
            1 for s in _COMPLEXITY_HIGH
            if (s in text.lower() if " " in s else s in _token_set(text))
        )
        if low_hits > high_hits:
            score = 2.0
            reason = "Text suggests low complexity."
        elif high_hits > low_hits:
            score = 0.0
            reason = "Text suggests high complexity."
        else:
            score = 1.0
            reason = "Moderate complexity inferred."
    return DimensionScore(name="complexity", score=score, reason=reason)


def _score_speed(text: str, time_to_revenue: str) -> DimensionScore:
    """Score speed to revenue 0-2."""
    lower = time_to_revenue.lower().strip()
    if lower in {"days", "1 week", "week", "fast", "immediate"}:
        score = 2.0
        reason = "Revenue possible within days/week."
    elif lower in {"2 weeks", "weeks", "1 month", "month"}:
        score = 1.5
        reason = "Revenue possible within weeks."
    elif lower in {"2 months", "months", "quarter"}:
        score = 1.0
        reason = "Revenue possible within months."
    elif lower in {"6 months", "year", "years", "long"}:
        score = 0.0
        reason = "Long time to revenue."
    else:
        fast_hits = sum(
            1 for s in _SPEED_FAST
            if (s in text.lower() if " " in s else s in _token_set(text))
        )
        slow_hits = sum(
            1 for s in _SPEED_SLOW
            if (s in text.lower() if " " in s else s in _token_set(text))
        )
        if fast_hits > slow_hits:
            score = 2.0
            reason = "Text suggests fast time to revenue."
        elif slow_hits > fast_hits:
            score = 0.5
            reason = "Text suggests slow time to revenue."
        else:
            score = 1.0
            reason = "Moderate speed to revenue inferred."
    return DimensionScore(name="speed_to_revenue", score=score, reason=reason)


def score_idea(
    *,
    idea_text: str,
    problem: str = "",
    target_user: str = "",
    monetization_model: str = "",
    competition_level: str = "",
    difficulty: str = "",
    time_to_revenue: str = "",
    differentiation: str = "",
    extra: dict[str, Any] | None = None,
) -> RevenueScore:
    """Score an idea on 5 revenue dimensions (0-10 total).

    Args:
        idea_text: Full idea description.
        problem: Problem statement.
        target_user: Target user description.
        monetization_model: Revenue model.
        competition_level: Market competition level.
        difficulty: Build difficulty.
        time_to_revenue: Expected time to first revenue.
        differentiation: Unique selling proposition.
        extra: Optional additional data.

    Returns:
        RevenueScore with total, breakdown, and decision.
    """
    combined = " ".join(filter(None, [
        idea_text, problem, target_user, monetization_model,
        competition_level, difficulty, time_to_revenue, differentiation,
    ]))

    dimensions = [
        _score_demand(combined),
        _score_monetization(combined),
        _score_saturation(combined, competition_level),
        _score_complexity(combined, difficulty),
        _score_speed(combined, time_to_revenue),
    ]

    total = sum(d.score for d in dimensions)
    # Clamp to 10.0 max
    total = min(total, 10.0)

    breakdown = {d.name: d.score for d in dimensions}

    if total >= 8.0:
        decision = ScoringDecision.APPROVE
        reason = f"Score {total}/10 — strong revenue potential. APPROVED for build."
    elif total >= 6.0:
        decision = ScoringDecision.HOLD
        reason = f"Score {total}/10 — moderate potential. HOLD for further validation."
    else:
        decision = ScoringDecision.REJECT
        reason = f"Score {total}/10 — insufficient revenue potential. REJECTED."

    return RevenueScore(
        total_score=total,
        decision=decision,
        dimensions=dimensions,
        breakdown=breakdown,
        decision_reason=reason,
    )
