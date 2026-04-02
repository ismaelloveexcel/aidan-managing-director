"""Tests for app.reasoning.idea_engine."""

from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import Idea


class TestIdeaGenerate:
    """Single idea generation tests."""

    def setup_method(self) -> None:
        self.engine = IdeaEngine()

    def test_returns_idea(self) -> None:
        idea = self.engine.generate("healthcare automation")
        assert isinstance(idea, Idea)

    def test_idea_has_required_fields(self) -> None:
        idea = self.engine.generate("healthcare automation")
        assert idea.idea_id
        assert idea.title
        assert idea.problem
        assert idea.target_user
        assert idea.monetization_path
        assert idea.difficulty
        assert idea.time_to_launch
        assert idea.summary

    def test_domain_from_context(self) -> None:
        idea = self.engine.generate("anything", context={"domain": "fintech"})
        assert "fintech" in idea.title.lower()

    def test_deterministic(self) -> None:
        a = self.engine.generate("healthcare automation")
        b = self.engine.generate("healthcare automation")
        assert a.idea_id == b.idea_id
        assert a.title == b.title


class TestIdeaBrainstorm:
    """Brainstorm tests."""

    def setup_method(self) -> None:
        self.engine = IdeaEngine()

    def test_returns_correct_count(self) -> None:
        ideas = self.engine.brainstorm("edtech tools", count=3)
        assert len(ideas) == 3
        assert all(isinstance(i, Idea) for i in ideas)

    def test_max_count_capped(self) -> None:
        ideas = self.engine.brainstorm("edtech", count=100)
        assert len(ideas) <= 5  # Only 5 templates

    def test_min_count(self) -> None:
        ideas = self.engine.brainstorm("edtech", count=0)
        assert len(ideas) == 1

    def test_all_ideas_unique(self) -> None:
        ideas = self.engine.brainstorm("fitness", count=5)
        ids = [i.idea_id for i in ideas]
        assert len(set(ids)) == len(ids)
