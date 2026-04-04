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
        for field in (
            "market_demand",
            "competition_saturation",
            "monetization_potential",
            "build_complexity",
            "speed_to_revenue",
        ):
            val = getattr(result.breakdown, field)
            assert 0.0 <= val <= 2.0
        assert 0.0 <= result.total_score <= 10.0

    def test_decision_in_mandatory_set(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert result.decision.value in {"REJECT", "HOLD", "APPROVE"}

    def test_reason_populated(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert len(result.reason) > 0

    def test_idea_id_matches(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.evaluator.score(idea)
        assert result.idea_id == idea.idea_id


class TestEvaluatorRank:
    """Ranking tests."""

    def setup_method(self) -> None:
        self.evaluator = Evaluator()
        self.engine = IdeaEngine()

    def test_rank_returns_sorted(self) -> None:
        ideas = self.engine.brainstorm("marketing tools", count=5)
        ranked = self.evaluator.rank(ideas)
        totals = [r.total_score for r in ranked]
        assert totals == sorted(totals, reverse=True)

    def test_rank_count_matches(self) -> None:
        ideas = self.engine.brainstorm("marketing tools", count=3)
        ranked = self.evaluator.rank(ideas)
        assert len(ranked) == 3
