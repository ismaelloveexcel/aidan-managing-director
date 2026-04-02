"""Tests for app.reasoning.evaluator."""

from app.reasoning.evaluator import Evaluator
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import EvaluationResult


class TestEvaluatorScore:
    """Scoring tests."""

    def setup_method(self) -> None:
        self.evaluator = Evaluator()
        self.engine = IdeaEngine()

    def test_returns_evaluation_result(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert isinstance(result, EvaluationResult)

    def test_scores_in_range(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        for field in ("feasibility", "profitability", "speed", "competition"):
            val = getattr(result.scores, field)
            assert 0.0 <= val <= 1.0

    def test_aggregate_in_range(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert 0.0 <= result.aggregate <= 1.0

    def test_recommendation_populated(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert len(result.recommendation) > 0

    def test_idea_id_matches(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert result.idea_id == idea.idea_id

    def test_custom_weights(self) -> None:
        evaluator = Evaluator(weights={
            "feasibility": 1.0,
            "profitability": 0.0,
            "speed": 0.0,
            "competition": 0.0,
        })
        idea = self.engine.generate("healthcare platform")
        result = evaluator.score(idea)
        assert result.aggregate == result.scores.feasibility


class TestEvaluatorRank:
    """Ranking tests."""

    def setup_method(self) -> None:
        self.evaluator = Evaluator()
        self.engine = IdeaEngine()

    def test_rank_returns_sorted(self) -> None:
        ideas = self.engine.brainstorm("marketing tools", count=5)
        ranked = self.evaluator.rank(ideas)
        aggregates = [r.aggregate for r in ranked]
        assert aggregates == sorted(aggregates, reverse=True)

    def test_rank_count_matches(self) -> None:
        ideas = self.engine.brainstorm("marketing tools", count=3)
        ranked = self.evaluator.rank(ideas)
        assert len(ranked) == 3
