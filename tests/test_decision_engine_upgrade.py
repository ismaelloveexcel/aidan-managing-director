"""Tests for Phase 2 decision-engine upgrades."""

from app.reasoning.evaluator import Evaluator
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import DecisionAction


def test_evaluator_outputs_all_weighted_dimensions() -> None:
    evaluator = Evaluator()
    idea = IdeaEngine().generate("freelancer proposal automation")
    result = evaluator.score(idea)

    assert 0.0 <= result.breakdown.market_demand <= 2.0
    assert 0.0 <= result.breakdown.competition_saturation <= 2.0
    assert 0.0 <= result.breakdown.monetization_potential <= 2.0
    assert 0.0 <= result.breakdown.build_complexity <= 2.0
    assert 0.0 <= result.breakdown.speed_to_revenue <= 2.0
    assert 0.0 <= result.total_score <= 10.0


def test_decision_output_contains_required_fields() -> None:
    evaluator = Evaluator()
    idea = IdeaEngine().generate("micro saas for accountants")
    result = evaluator.score(idea)

    assert result.reason
    assert result.decision in {
        DecisionAction.APPROVE,
        DecisionAction.REJECT,
        DecisionAction.HOLD,
    }

