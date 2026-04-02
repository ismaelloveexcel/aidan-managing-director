"""Tests for app.reasoning.strategist."""

from app.reasoning.models import IntentType
from app.reasoning.strategist import Strategist


class TestStrategyClassification:
    """Intent classification tests."""

    def setup_method(self) -> None:
        self.strategist = Strategist()

    def test_build_intent(self) -> None:
        result = self.strategist.analyse({"message": "I want to build a new product"})
        assert result.intent == IntentType.BUILD
        assert result.confidence > 0

    def test_improve_intent(self) -> None:
        result = self.strategist.analyse({"message": "We need to improve our app"})
        assert result.intent == IntentType.IMPROVE

    def test_explore_intent(self) -> None:
        result = self.strategist.analyse({"message": "Let's brainstorm some ideas"})
        assert result.intent == IntentType.EXPLORE

    def test_monetise_intent(self) -> None:
        result = self.strategist.analyse({"message": "How can we monetize this?"})
        assert result.intent == IntentType.MONETISE

    def test_pivot_intent(self) -> None:
        result = self.strategist.analyse({"message": "We should pivot to a new direction"})
        assert result.intent == IntentType.PIVOT

    def test_unknown_intent(self) -> None:
        result = self.strategist.analyse({"message": "hello there"})
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_empty_message(self) -> None:
        result = self.strategist.analyse({"message": ""})
        assert result.intent == IntentType.UNKNOWN

    def test_missing_message_key(self) -> None:
        result = self.strategist.analyse({})
        assert result.intent == IntentType.UNKNOWN

    def test_objectives_populated(self) -> None:
        result = self.strategist.analyse({"message": "build a SaaS tool"})
        assert len(result.objectives) > 0

    def test_user_goals_included(self) -> None:
        result = self.strategist.analyse({
            "message": "build something",
            "goals": ["Reach 100 users"],
        })
        assert "Reach 100 users" in result.objectives

    def test_direction_populated(self) -> None:
        result = self.strategist.analyse({"message": "build a tool"})
        assert len(result.direction) > 0

    def test_priority_populated(self) -> None:
        result = self.strategist.analyse({"message": "build a tool"})
        assert result.priority == "execution"


class TestPrioritise:
    """Objective prioritisation tests."""

    def setup_method(self) -> None:
        self.strategist = Strategist()

    def test_empty_list(self) -> None:
        assert self.strategist.prioritise([]) == []

    def test_sorted_by_length(self) -> None:
        objectives = ["Long objective description", "Short", "Mid-size obj"]
        result = self.strategist.prioritise(objectives)
        assert result == ["Short", "Mid-size obj", "Long objective description"]

    def test_single_objective(self) -> None:
        assert self.strategist.prioritise(["Only one"]) == ["Only one"]
