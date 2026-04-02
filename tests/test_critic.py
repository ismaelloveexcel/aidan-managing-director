"""Tests for app.reasoning.critic."""

from app.reasoning.critic import Critic
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import CritiqueResult, Difficulty, Idea


class TestCriticCritique:
    """Critique tests."""

    def setup_method(self) -> None:
        self.critic = Critic()
        self.engine = IdeaEngine()

    def test_returns_critique_result(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.critic.critique(idea)
        assert isinstance(result, CritiqueResult)

    def test_assumptions_non_empty(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.critic.critique(idea)
        assert len(result.assumptions_challenged) > 0

    def test_risks_non_empty(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.critic.critique(idea)
        assert len(result.risks) > 0

    def test_improvements_non_empty(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.critic.critique(idea)
        assert len(result.improvements) > 0

    def test_verdict_valid(self) -> None:
        idea = self.engine.generate("healthcare platform")
        result = self.critic.critique(idea)
        assert result.verdict in ("proceed", "revise", "reject")

    def test_high_difficulty_triggers_weakness(self) -> None:
        idea = Idea(
            idea_id="test-1",
            title="Complex Marketplace",
            problem="Hard problem to solve with many unknowns",
            target_user="enterprise users",
            monetization_path="Transaction fee on completed jobs",
            difficulty=Difficulty.HIGH,
            time_to_launch="6 months",
            summary="A complex venture.",
        )
        result = self.critic.critique(idea)
        assert any("difficulty" in w.lower() for w in result.weaknesses)

    def test_marketplace_risk(self) -> None:
        idea = Idea(
            idea_id="test-2",
            title="Marketplace for Freelancers",
            problem="Finding freelancers is hard",
            target_user="businesses",
            monetization_path="Transaction fee",
            difficulty=Difficulty.HIGH,
            time_to_launch="3 months",
            summary="A marketplace.",
        )
        result = self.critic.critique(idea)
        assert any("chicken-and-egg" in r.description.lower() for r in result.risks)
