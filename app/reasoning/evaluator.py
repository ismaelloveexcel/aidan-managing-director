"""
evaluator.py – Objective scoring and evaluation of ideas and plans.

Scores :class:`Idea` instances against feasibility, profitability, speed,
and competition criteria using deterministic heuristics.
"""

from __future__ import annotations

from app.reasoning.models import (
    Difficulty,
    EvaluationResult,
    EvaluationScores,
    Idea,
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
    "feasibility": 0.30,
    "profitability": 0.30,
    "speed": 0.20,
    "competition": 0.20,
}


class Evaluator:
    """Scores and ranks :class:`Idea` instances using deterministic heuristics.

    No external API calls are made.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        _required_keys = set(_DEFAULT_WEIGHTS)
        missing = _required_keys - set(self._weights)
        if missing:
            raise ValueError(
                f"Weights must include all scoring criteria. Missing: {sorted(missing)}"
            )
        for key, value in self._weights.items():
            if value < 0:
                raise ValueError(
                    f"Weight for '{key}' must be non-negative, got {value}"
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, idea: Idea) -> EvaluationResult:
        """Score a single *idea* and return an :class:`EvaluationResult`."""
        scores = EvaluationScores(
            feasibility=self._score_feasibility(idea),
            profitability=self._score_profitability(idea),
            speed=self._score_speed(idea),
            competition=self._score_competition(idea),
        )
        aggregate = self._aggregate(scores)
        recommendation = self._recommend(aggregate)
        return EvaluationResult(
            idea_id=idea.idea_id,
            scores=scores,
            aggregate=aggregate,
            recommendation=recommendation,
        )

    def rank(self, ideas: list[Idea]) -> list[EvaluationResult]:
        """Score and rank a list of ideas from highest to lowest aggregate."""
        results = [self.score(idea) for idea in ideas]
        results.sort(key=lambda r: r.aggregate, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Scoring heuristics
    # ------------------------------------------------------------------

    @staticmethod
    def _score_feasibility(idea: Idea) -> float:
        return _DIFFICULTY_FEASIBILITY.get(idea.difficulty, 0.5)

    @staticmethod
    def _score_profitability(idea: Idea) -> float:
        """Estimate profitability from the monetization path description."""
        path = idea.monetization_path.lower()
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

    def _aggregate(self, scores: EvaluationScores) -> float:
        """Compute the weighted aggregate of *scores*."""
        total = (
            scores.feasibility * self._weights["feasibility"]
            + scores.profitability * self._weights["profitability"]
            + scores.speed * self._weights["speed"]
            + scores.competition * self._weights["competition"]
        )
        return round(total, 2)

    @staticmethod
    def _recommend(aggregate: float) -> str:
        """Return a short recommendation string based on *aggregate*."""
        if aggregate >= 0.75:
            return "Strong candidate — prioritise for execution."
        if aggregate >= 0.55:
            return "Viable option — worth further exploration."
        if aggregate >= 0.35:
            return "Marginal — needs significant de-risking."
        return "Weak — consider discarding or pivoting."
