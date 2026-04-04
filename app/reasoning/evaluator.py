"""
evaluator.py – Deterministic AI-DAN 0–10 scoring engine.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.supervisor import validate_market_truth
from app.reasoning.models import (
    DecisionAction,
    Difficulty,
    EvaluationResult,
    EvaluationScores,
    Idea,
    PortfolioComparisonEntry,
)


class Evaluator:
    """Scores and ranks :class:`Idea` instances using mandatory 0–10 rules."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        # Legacy/custom weights are intentionally ignored in the mandatory model.
        _ = weights

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        idea: Idea,
        market_truth: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Score a single *idea* with the mandatory deterministic model."""
        truth = market_truth or validate_market_truth(self._idea_validation_payload(idea))
        gate_decision = str(truth.get("decision", "FAIL")).upper()
        gate_reason = str(truth.get("reason", "Market truth validation failed."))
        if gate_decision != "PASS":
            zero = EvaluationScores(
                market_demand=0.0,
                competition_saturation=0.0,
                monetization_potential=0.0,
                build_complexity=0.0,
                speed_to_revenue=0.0,
            )
            return EvaluationResult(
                idea_id=idea.idea_id,
                total_score=0.0,
                breakdown=zero,
                decision=DecisionAction.REJECT,
                reason=f"Validation Gate 0 failed: {gate_reason}",
            )

        breakdown = EvaluationScores(
            market_demand=self._score_market_demand(str(truth.get("demand_level", "LOW"))),
            competition_saturation=self._score_competition_saturation(
                market_saturation=str(truth.get("market_saturation", "HIGH")),
                differentiation_detected=bool(truth.get("differentiation_detected", False)),
            ),
            monetization_potential=self._score_monetization_potential(
                idea=idea,
                monetization_proof=bool(truth.get("monetization_proof", False)),
            ),
            build_complexity=self._score_build_complexity(idea.difficulty),
            speed_to_revenue=self._score_speed_to_revenue(idea.time_to_launch),
        )
        total_score = round(
            breakdown.market_demand
            + breakdown.competition_saturation
            + breakdown.monetization_potential
            + breakdown.build_complexity
            + breakdown.speed_to_revenue,
            2,
        )
        decision = self._decision(total_score)
        return EvaluationResult(
            idea_id=idea.idea_id,
            decision=decision,
            reason=self._decision_reason(total_score, breakdown),
            total_score=total_score,
            breakdown=breakdown,
        )

    def rank(self, ideas: list[Idea]) -> list[EvaluationResult]:
        """Score and rank a list of ideas from highest to lowest total score."""
        results = [self.score(idea) for idea in ideas]
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results

    def compare_against_portfolio(
        self,
        candidate: Idea,
        portfolio_ideas: list[Idea],
    ) -> list[PortfolioComparisonEntry]:
        """Compare candidate idea to existing portfolio ideas by total score."""
        candidate_score = self.score(candidate).total_score
        comparisons: list[PortfolioComparisonEntry] = []
        for existing in portfolio_ideas:
            existing_score = self.score(existing).total_score
            score_delta = round(candidate_score - existing_score, 2)
            comparisons.append(
                PortfolioComparisonEntry(
                    project_id=existing.idea_id,
                    project_name=existing.title,
                    overlap_score=0.0,
                    overlap_reasons=["Deterministic score-only comparison."],
                    candidate_idea_id=candidate.idea_id,
                    existing_idea_id=existing.idea_id,
                    candidate_score=candidate_score,
                    existing_score=existing_score,
                    score_delta=score_delta,
                    recommendation=(
                        "prioritize_candidate"
                        if candidate_score >= existing_score
                        else "keep_existing_priority"
                    ),
                ),
            )
        comparisons.sort(key=lambda item: item.score_delta or 0.0, reverse=True)
        return comparisons

    # ------------------------------------------------------------------
    # Scoring rules (mandatory)
    # ------------------------------------------------------------------

    @staticmethod
    def _idea_validation_payload(idea: Idea) -> dict[str, Any]:
        return {
            "title": idea.title,
            "hypothesis": idea.summary,
            "target_user": idea.target_user,
            "problem": idea.problem,
            "solution": idea.summary,
            "pricing_hint": idea.monetization_path,
            "monetization_path": idea.monetization_path,
        }

    @staticmethod
    def _score_market_demand(demand_level: str) -> float:
        level = demand_level.upper()
        if level == "HIGH":
            return 2.0
        if level == "MEDIUM":
            return 1.0
        return 0.0

    @staticmethod
    def _score_competition_saturation(
        *,
        market_saturation: str,
        differentiation_detected: bool,
    ) -> float:
        saturation = market_saturation.upper()
        if saturation == "LOW":
            return 2.0
        if saturation == "MEDIUM":
            return 1.5 if differentiation_detected else 0.5
        return 1.0 if differentiation_detected else 0.0

    @staticmethod
    def _score_monetization_potential(*, idea: Idea, monetization_proof: bool) -> float:
        if not monetization_proof:
            return 0.0
        path = idea.monetization_path.lower()
        if "subscription" in path or "saas" in path or "retainer" in path:
            return 2.0
        if "transaction" in path or "license" in path or "per seat" in path:
            return 1.5
        if "enterprise" in path or "premium" in path or "one-time" in path:
            return 1.5
        # When validation confirms monetization proof, retain minimum viability.
        return 1.5

    @staticmethod
    def _score_build_complexity(difficulty: Difficulty) -> float:
        if difficulty == Difficulty.LOW:
            return 2.0
        if difficulty == Difficulty.MEDIUM:
            return 1.0
        return 0.0

    @staticmethod
    def _score_speed_to_revenue(time_to_launch: str) -> float:
        text = time_to_launch.lower()
        week_match = re.search(r"(\d+)\s*week", text)
        month_match = re.search(r"(\d+)\s*month", text)
        if week_match:
            weeks = int(week_match.group(1))
            if weeks <= 4:
                return 2.0
            if weeks <= 8:
                return 1.5
            return 1.0
        if month_match:
            months = int(month_match.group(1))
            if months <= 1:
                return 1.5
            if months <= 3:
                return 1.0
            return 0.5
        # Unknown duration defaults to cautious medium.
        return 1.0

    @staticmethod
    def _decision(total_score: float) -> DecisionAction:
        if total_score < 6.0:
            return DecisionAction.REJECT
        if total_score < 8.0:
            return DecisionAction.HOLD
        return DecisionAction.APPROVE

    @staticmethod
    def _decision_reason(total_score: float, breakdown: EvaluationScores) -> str:
        if total_score < 6.0:
            return (
                "Score below 6.0: reject and rework market demand/monetization before build."
            )
        if total_score < 8.0:
            weakest = min(
                {
                    "market_demand": breakdown.market_demand,
                    "competition_saturation": breakdown.competition_saturation,
                    "monetization_potential": breakdown.monetization_potential,
                    "build_complexity": breakdown.build_complexity,
                    "speed_to_revenue": breakdown.speed_to_revenue,
                },
                key=lambda key: {
                    "market_demand": breakdown.market_demand,
                    "competition_saturation": breakdown.competition_saturation,
                    "monetization_potential": breakdown.monetization_potential,
                    "build_complexity": breakdown.build_complexity,
                    "speed_to_revenue": breakdown.speed_to_revenue,
                }[key],
            )
            return f"Score in HOLD band (6-7). Improve weakest axis: {weakest}."
        return "Score is 8+ with acceptable risk profile: approved for business packaging."
