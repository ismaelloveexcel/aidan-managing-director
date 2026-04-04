"""
Guardian agent for feasibility and scope risk checks.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class GuardianReviewResult(BaseModel):
    """Structured output from guardian review."""

    decision: Literal["APPROVE", "FLAG", "BLOCK"]
    reason: str
    risk_flags: list[str] = Field(default_factory=list)


class CompetitionHeuristic(BaseModel):
    """Deterministic competitor and saturation projection."""

    competitor_count: int = Field(ge=0)
    market_saturation: Literal["LOW", "MEDIUM", "HIGH"]
    differentiation_detected: bool
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_categories: list[str] = Field(default_factory=list)


class GuardianAgent:
    """Deterministic guardrail checks before factory execution."""

    _CATEGORY_RULES: dict[str, tuple[tuple[str, ...], int]] = {
        "ai_recruiting": (("cv", "resume", "job", "recruit", "talent"), 16),
        "ai_assistant": (("assistant", "copilot", "agent", "chatbot"), 14),
        "analytics_dashboard": (("dashboard", "analytics", "reporting", "kpi"), 12),
        "marketplace": (("marketplace", "freelancer", "gig", "vendor"), 10),
        "education": (("course", "learning", "education", "certification"), 9),
        "workflow_automation": (("automation", "workflow", "integrations", "ops"), 11),
    }

    _GENERIC_SIMILARITY_TERMS: tuple[str, ...] = (
        "ai",
        "tool",
        "platform",
        "assistant",
        "dashboard",
        "marketplace",
        "saas",
    )

    _DIFFERENTIATION_TERMS: tuple[str, ...] = (
        "niche",
        "vertical",
        "local",
        "region",
        "compliance",
        "workflow",
        "real-time",
        "automated",
        "specific",
        "exclusive",
        "personalized",
    )

    def assess_competition(self, *, build_brief: dict[str, Any]) -> CompetitionHeuristic:
        """Estimate competitor count and differentiation via keyword/category matching."""
        title = str(build_brief.get("title", "")).lower()
        problem = str(build_brief.get("problem", "")).lower()
        solution = str(build_brief.get("solution", "")).lower()
        target_user = str(build_brief.get("target_user", "")).lower()
        combined_text = f"{title} {problem} {solution} {target_user}".strip()

        matched_categories: list[str] = []
        baseline_competitors = 3
        for category, (keywords, baseline) in self._CATEGORY_RULES.items():
            if any(keyword in combined_text for keyword in keywords):
                matched_categories.append(category)
                baseline_competitors = max(baseline_competitors, baseline)

        competitor_count = baseline_competitors + max(0, len(matched_categories) - 1) * 2

        generic_hits = sum(1 for token in self._GENERIC_SIMILARITY_TERMS if token in combined_text)
        similarity_score = min(1.0, round(0.25 + (generic_hits * 0.1) + (len(matched_categories) * 0.08), 2))

        differentiation_detected = (
            any(term in solution for term in self._DIFFERENTIATION_TERMS)
            or any(term in target_user for term in self._DIFFERENTIATION_TERMS)
            or len(re.findall(r"\b[a-z0-9\-]+\b", target_user)) >= 4
        )

        if competitor_count >= 12:
            saturation: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
        elif competitor_count >= 7:
            saturation = "MEDIUM"
        else:
            saturation = "LOW"

        return CompetitionHeuristic(
            competitor_count=competitor_count,
            market_saturation=saturation,
            differentiation_detected=differentiation_detected,
            similarity_score=similarity_score,
            matched_categories=matched_categories,
        )

    def review(
        self,
        *,
        idea_input: dict[str, Any],
        validation_score: float,
        monetization_model: str,
        market_truth: dict[str, Any] | None = None,
    ) -> GuardianReviewResult:
        """Run feasibility, overlap, monetization, and scope checks."""
        risk_flags: list[str] = []

        mvp_scope = idea_input.get("mvp_scope", [])
        pricing_hint = str(idea_input.get("pricing_hint", "")).strip()
        competition = self.assess_competition(build_brief=idea_input)

        if validation_score < 0.45:
            risk_flags.append("low_validation_score")

        if competition.market_saturation == "HIGH" and not competition.differentiation_detected:
            risk_flags.append("high_saturation_no_differentiation")
        if competition.similarity_score >= 0.75:
            risk_flags.append("possible_duplicate_overlap")

        if not monetization_model.strip() and not pricing_hint:
            risk_flags.append("missing_monetization_logic")
        if market_truth is not None and str(market_truth.get("decision", "")).upper() == "FAIL":
            risk_flags.append("market_truth_failed")

        if not isinstance(mvp_scope, list) or len(mvp_scope) == 0:
            risk_flags.append("missing_scope")
        elif len(mvp_scope) > 8:
            risk_flags.append("scope_too_large")
        elif len(mvp_scope) > 5:
            risk_flags.append("scope_risk_medium")

        if (
            "scope_too_large" in risk_flags
            or "missing_scope" in risk_flags
            or "market_truth_failed" in risk_flags
        ):
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
