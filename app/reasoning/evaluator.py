"""
evaluator.py – Objective scoring and evaluation of ideas and plans.

Implements a weighted decision score across business and execution axes.
"""

from __future__ import annotations

import re

from app.reasoning.models import (
    DecisionAction,
    Difficulty,
    EvaluationDecision,
    EvaluationResult,
    EvaluationScores,
    Idea,
    PortfolioComparisonEntry,
)

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

_DIFFICULTY_FEASIBILITY: dict[Difficulty, float] = {
    Difficulty.LOW: 0.9,
    Difficulty.MEDIUM: 0.6,
    Difficulty.HIGH: 0.3,
}

_DIFFICULTY_SPEED: dict[Difficulty, float] = {
    Difficulty.LOW: 0.9,
    Difficulty.MEDIUM: 0.5,
    Difficulty.HIGH: 0.2,
}

_DEFAULT_WEIGHTS: dict[str, float] = {
    "demand": 0.16,
    "monetization_clarity": 0.14,
    "speed_to_mvp": 0.14,
    "competition": 0.10,
    "execution_simplicity": 0.14,
    "scalability": 0.10,
    "founder_fit": 0.10,
    "risk": 0.12,
}

_LEGACY_REQUIRED_WEIGHTS: set[str] = {"feasibility", "profitability", "speed", "competition"}
_NEW_REQUIRED_WEIGHTS: set[str] = set(_DEFAULT_WEIGHTS)


class Evaluator:
    """Scores and ranks :class:`Idea` instances using deterministic heuristics.

    No external API calls are made.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._legacy_weight_mode = False
        self._weights = dict(_DEFAULT_WEIGHTS)
        self._legacy_weights: dict[str, float] | None = None

        if weights is None:
            return

        provided_keys = set(weights)
        if provided_keys == _NEW_REQUIRED_WEIGHTS:
            self._weights = dict(weights)
        elif provided_keys == _LEGACY_REQUIRED_WEIGHTS:
            self._legacy_weight_mode = True
            self._legacy_weights = dict(weights)
        else:
            missing_new = sorted(_NEW_REQUIRED_WEIGHTS - provided_keys)
            missing_legacy = sorted(_LEGACY_REQUIRED_WEIGHTS - provided_keys)
            raise ValueError(
                "Weights must include all scoring criteria. "
                f"Missing (new schema): {missing_new}; "
                f"Missing (legacy schema): {missing_legacy}"
            )

        for key, value in weights.items():
            if value < 0:
                raise ValueError(f"Weight for '{key}' must be non-negative, got {value}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, idea: Idea) -> EvaluationResult:
        """Score a single *idea* and return an :class:`EvaluationResult`."""
        demand = self._score_demand(idea)
        monetization = self._score_monetization_clarity(idea)
        speed_to_mvp = self._score_speed(idea)
        competition = self._score_competition(idea)
        execution_simplicity = self._score_execution_simplicity(idea)
        scalability = self._score_scalability(idea)
        founder_fit = self._score_founder_fit(idea)
        risk = self._score_risk(idea)

        axis_scores = {
            "demand": demand,
            "monetization_clarity": monetization,
            "speed_to_mvp": speed_to_mvp,
            "competition": competition,
            "execution_simplicity": execution_simplicity,
            "scalability": scalability,
            "founder_fit": founder_fit,
            "risk": risk,
        }

        scores = EvaluationScores(
            demand=demand,
            monetization_clarity=monetization,
            speed_to_mvp=speed_to_mvp,
            competition=competition,
            execution_simplicity=execution_simplicity,
            scalability=scalability,
            founder_fit=founder_fit,
            risk=risk,
            feasibility=execution_simplicity,
            profitability=monetization,
            speed=speed_to_mvp,
        )
        aggregate = self._aggregate(axis_scores, scores)
        recommendation = self._recommend(aggregate)
        decision = self._decision_payload(idea=idea, aggregate=aggregate, axis_scores=axis_scores)
        return EvaluationResult(
            idea_id=idea.idea_id,
            scores=scores,
            aggregate=aggregate,
            recommendation=recommendation,
            decision=decision,
        )

    def rank(self, ideas: list[Idea]) -> list[EvaluationResult]:
        """Score and rank a list of ideas from highest to lowest aggregate."""
        results = [self.score(idea) for idea in ideas]
        results.sort(key=lambda r: r.aggregate, reverse=True)
        return results

    def compare_against_portfolio(
        self,
        candidate: Idea,
        portfolio_ideas: list[Idea],
    ) -> list[PortfolioComparisonEntry]:
        """Compare candidate idea to existing portfolio ideas by aggregate score."""
        candidate_score = self.score(candidate).aggregate
        comparisons: list[PortfolioComparisonEntry] = []
        for existing in portfolio_ideas:
            existing_score = self.score(existing).aggregate
            comparisons.append(
                PortfolioComparisonEntry(
                    candidate_idea_id=candidate.idea_id,
                    existing_idea_id=existing.idea_id,
                    candidate_score=candidate_score,
                    existing_score=existing_score,
                    score_delta=round(candidate_score - existing_score, 2),
                    recommendation=(
                        "prioritize_candidate"
                        if candidate_score >= existing_score
                        else "keep_existing_priority"
                    ),
                ),
            )
        comparisons.sort(key=lambda item: item.score_delta, reverse=True)
        return comparisons

    # ------------------------------------------------------------------
    # Scoring heuristics
    # ------------------------------------------------------------------

    @staticmethod
    def _score_demand(idea: Idea) -> float:
        problem = idea.problem.lower()
        target_user = idea.target_user.lower()
        score = 0.5
        if any(token in problem for token in ("waste", "slow", "time-consuming", "fragmented", "hard")):
            score += 0.2
        if any(token in target_user for token in ("business", "teams", "professionals", "developers")):
            score += 0.15
        if "beginners" in target_user:
            score -= 0.05
        return max(0.0, min(1.0, score))

    @staticmethod
    def _score_monetization_clarity(idea: Idea) -> float:
        """Estimate monetization clarity from monetization path language."""
        path = idea.monetization_path.lower()
        if ("subscription" in path or "saas" in path) and re.search(r"\$|\d", path):
            return 0.9
        if "subscription" in path or "saas" in path:
            return 0.8
        if "fee" in path or "transaction" in path:
            return 0.7
        if "freemium" in path or "premium" in path:
            return 0.6
        if "course" in path or "certification" in path:
            return 0.5
        if "support" in path or "enterprise" in path:
            return 0.55
        return 0.4

    @staticmethod
    def _score_speed(idea: Idea) -> float:
        return _DIFFICULTY_SPEED.get(idea.difficulty, 0.5)

    @staticmethod
    def _score_execution_simplicity(idea: Idea) -> float:
        return _DIFFICULTY_FEASIBILITY.get(idea.difficulty, 0.5)

    @staticmethod
    def _score_competition(idea: Idea) -> float:
        """Estimate competitive advantage from idea attributes.

        Ideas targeting niche users or featuring lower difficulty are assumed
        to face less competition.
        """
        score = 0.5
        if idea.difficulty == Difficulty.LOW:
            score += 0.15
        if len(idea.target_user) > 30:
            # Longer target-user description implies narrower niche.
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _score_scalability(idea: Idea) -> float:
        path = idea.monetization_path.lower()
        if "subscription" in path or "saas" in path:
            return 0.85
        if "transaction" in path or "marketplace" in idea.title.lower():
            return 0.65
        if "course" in path:
            return 0.5
        return 0.45

    @staticmethod
    def _score_founder_fit(idea: Idea) -> float:
        user = idea.target_user.lower()
        if "developer" in user or "freelancer" in user or "small-business" in user:
            return 0.8
        if "enterprise" in user:
            return 0.45
        return 0.6

    @staticmethod
    def _score_risk(idea: Idea) -> float:
        if idea.difficulty == Difficulty.LOW:
            return 0.8
        if idea.difficulty == Difficulty.MEDIUM:
            return 0.6
        return 0.35

    def _aggregate(self, axis_scores: dict[str, float], scores: EvaluationScores) -> float:
        """Compute the weighted aggregate of axis scores."""
        total = 0.0
        if self._legacy_weight_mode and self._legacy_weights is not None:
            total += scores.feasibility * self._legacy_weights["feasibility"]
            total += scores.profitability * self._legacy_weights["profitability"]
            total += scores.speed * self._legacy_weights["speed"]
            total += scores.competition * self._legacy_weights["competition"]
            return round(total, 2)

        for key, weight in self._weights.items():
            total += axis_scores[key] * weight
        return round(total, 2)

    @staticmethod
    def _recommend(aggregate: float) -> str:
        """Return a short recommendation string based on *aggregate*."""
        if aggregate >= 0.8:
            return "Strong candidate — prioritise for execution."
        if aggregate >= 0.6:
            return "Viable option — worth further exploration."
        if aggregate >= 0.45:
            return "Marginal — needs significant de-risking."
        return "Weak — consider discarding or pivoting."

    @staticmethod
    def _decision_payload(
        *,
        idea: Idea,
        aggregate: float,
        axis_scores: dict[str, float],
    ) -> EvaluationDecision:
        """Build UI-friendly strategic decision payload."""
        if aggregate >= 0.75:
            action = DecisionAction.APPROVE
            recommended = "Queue for build with strict MVP scope."
        elif aggregate >= 0.55:
            action = DecisionAction.PARK
            recommended = "Run faster demand validation before build."
        else:
            action = DecisionAction.REJECT
            recommended = "Do not allocate build capacity to this idea."

        weakest_axis = min(axis_scores, key=lambda key: axis_scores[key])
        risk_map = {
            "demand": "Demand signal is currently weak.",
            "monetization_clarity": "Monetization path lacks clarity.",
            "speed_to_mvp": "Time-to-MVP may be too slow.",
            "competition": "Competitive pressure may be high.",
            "execution_simplicity": "Execution complexity is high.",
            "scalability": "Scaling path is uncertain.",
            "founder_fit": "Founder-market fit is uncertain.",
            "risk": "Overall execution risk is elevated.",
        }
        why_now = (
            f"Current aggregate score is {aggregate:.2f} with strongest "
            f"signals in {max(axis_scores, key=lambda key: axis_scores[key]).replace('_', ' ')}."
        )
        return EvaluationDecision(
            verdict=action.value,
            why_now=why_now,
            main_risk=risk_map[weakest_axis],
            recommended_next_move=recommended,
            action=action,
        )
