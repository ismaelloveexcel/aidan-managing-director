"""
Deterministic input validation for the multi-layer build pipeline.
"""

from __future__ import annotations

import re
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.guardian import GuardianAgent


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


class MarketTruthValidationResult(BaseModel):
    """Hard market-truth gate result used before any scoring."""

    demand_level: Literal["HIGH", "MEDIUM", "LOW"]
    monetization_proof: bool
    market_saturation: Literal["LOW", "MEDIUM", "HIGH"]
    competitor_count: int = Field(ge=0)
    differentiation_detected: bool
    decision: Literal["PASS", "FAIL"]
    reason: str


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


def _detect_demand_level(build_brief: dict[str, Any]) -> Literal["HIGH", "MEDIUM", "LOW"]:
    """Classify demand level from problem urgency and audience specificity."""
    hypothesis = str(build_brief.get("hypothesis", "")).lower()
    problem = str(build_brief.get("problem", "")).lower()
    target_user = str(build_brief.get("target_user", "")).lower()
    text = f"{hypothesis} {problem}"

    urgency_terms = (
        "slow",
        "expensive",
        "manual",
        "time-consuming",
        "waste",
        "pain",
        "error",
        "compliance",
        "urgent",
        "revenue",
    )
    urgency_hits = sum(1 for token in urgency_terms if token in text)
    broad_audience = any(term in target_user for term in ("everyone", "all users", "general"))
    specific_audience = len([token for token in target_user.split() if len(token) > 3]) >= 2

    if urgency_hits >= 3 and specific_audience and not broad_audience:
        return "HIGH"
    if urgency_hits >= 1 and not broad_audience:
        return "MEDIUM"
    return "LOW"


def _detect_monetization_proof(build_brief: dict[str, Any]) -> bool:
    """Detect concrete monetization proof from pricing and model signals."""
    pricing_hint = str(build_brief.get("pricing_hint", "")).lower()
    monetization_text = str(
        build_brief.get("monetization_path", build_brief.get("pricing_hint", "")),
    ).lower()
    text = f"{pricing_hint} {monetization_text}"

    paid_model_terms = (
        "subscription",
        "monthly",
        "annual",
        "one-time",
        "freemium",
        "premium",
        "transaction",
        "course",
        "certification",
        "support",
        "fee",
        "license",
        "paid",
        "pricing",
        "plan",
        "per seat",
        "retainer",
        "enterprise",
    )
    has_paid_model = any(term in text for term in paid_model_terms)
    has_price = bool(
        re.search(
            r"(\$|usd|eur|gbp)\s*\d+|\b\d+\s*(/mo|per month|monthly|yearly|per year)\b|\b\d+\s*%|\b\d+\s*[–-]\s*\d+\s*%",
            text,
        ),
    )
    has_fee_signal = "fee" in text or "fees" in text
    return has_paid_model and (has_price or has_fee_signal)


def validate_market_truth(build_brief: dict[str, Any]) -> MarketTruthValidationResult:
    """Apply a strict market-truth gate before evaluator/scoring."""
    guardian = GuardianAgent()
    competition = guardian.assess_competition(build_brief=build_brief)
    demand_level = _detect_demand_level(build_brief)
    monetization_proof = _detect_monetization_proof(build_brief)

    if demand_level == "LOW":
        return MarketTruthValidationResult(
            demand_level=demand_level,
            monetization_proof=monetization_proof,
            market_saturation=competition.market_saturation,
            competitor_count=competition.competitor_count,
            differentiation_detected=competition.differentiation_detected,
            decision="FAIL",
            reason="Demand level is LOW based on weak urgency and audience specificity.",
        )

    if not monetization_proof:
        return MarketTruthValidationResult(
            demand_level=demand_level,
            monetization_proof=False,
            market_saturation=competition.market_saturation,
            competitor_count=competition.competitor_count,
            differentiation_detected=competition.differentiation_detected,
            decision="FAIL",
            reason="Monetization proof missing: no concrete paid pricing signal detected.",
        )

    if competition.market_saturation == "HIGH" and not competition.differentiation_detected:
        return MarketTruthValidationResult(
            demand_level=demand_level,
            monetization_proof=monetization_proof,
            market_saturation=competition.market_saturation,
            competitor_count=competition.competitor_count,
            differentiation_detected=False,
            decision="FAIL",
            reason="Market saturation is HIGH without credible differentiation.",
        )

    return MarketTruthValidationResult(
        demand_level=demand_level,
        monetization_proof=monetization_proof,
        market_saturation=competition.market_saturation,
        competitor_count=competition.competitor_count,
        differentiation_detected=competition.differentiation_detected,
        decision="PASS",
        reason="Market truth validation passed.",
    )
