"""Tests for Phase 2 decision-engine upgrades."""

from app.reasoning.evaluator import Evaluator
from app.reasoning.idea_engine import IdeaEngine
from app.reasoning.models import DecisionAction


def test_evaluator_outputs_all_weighted_dimensions() -> None:
    evaluator = Evaluator()
    idea = IdeaEngine().generate("freelancer proposal automation")
    result = evaluator.score(idea)

    assert 0.0 <= result.scores.demand <= 1.0
    assert 0.0 <= result.scores.monetization_clarity <= 1.0
    assert 0.0 <= result.scores.speed_to_mvp <= 1.0
    assert 0.0 <= result.scores.competition <= 1.0
    assert 0.0 <= result.scores.execution_simplicity <= 1.0
    assert 0.0 <= result.scores.scalability <= 1.0
    assert 0.0 <= result.scores.founder_fit <= 1.0
    assert 0.0 <= result.scores.risk <= 1.0


def test_decision_output_contains_required_fields() -> None:
    evaluator = Evaluator()
    idea = IdeaEngine().generate("micro saas for accountants")
    result = evaluator.score(idea)

    decision = result.decision
    assert decision.verdict
    assert decision.why_now
    assert decision.main_risk
    assert decision.recommended_next_move
    assert decision.action in {
        DecisionAction.APPROVE,
        DecisionAction.REJECT,
        DecisionAction.PARK,
    }

