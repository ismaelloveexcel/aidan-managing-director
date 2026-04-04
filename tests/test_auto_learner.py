"""Tests for the auto-learning system."""

import pytest

from app.memory.auto_learner import AutoLearner, ScoringWeights
from app.memory.store import MemoryStore


def test_initial_weights_are_defaults() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    weights = learner.current_weights
    assert weights.demand == 1.0
    assert weights.speed == 1.0


def test_record_outcome_creates_signal_and_event() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    learner.record_outcome(
        project_id="p1", outcome_type="build_success", score=0.9,
    )
    events = store.recent_events(limit=10)
    assert len(events) == 1
    assert events[0]["event_type"] == "auto_learning"
    signals = store.get_project_signals("p1")
    assert len(signals) == 1
    assert signals[0].signal_type == "build_success"


def test_record_outcome_rejects_invalid_type() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    with pytest.raises(ValueError, match="Invalid outcome_type"):
        learner.record_outcome(
            project_id="p1", outcome_type="unknown_type", score=0.5,  # type: ignore[arg-type]
        )


def test_record_outcome_clamps_score_in_event() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    learner.record_outcome(project_id="p1", outcome_type="build_success", score=1.5)
    events = store.recent_events(limit=10)
    assert events[0]["score"] == 1.0


def test_generate_insight_empty() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    insight = learner.generate_insight()
    assert insight.total_signals == 0
    assert insight.success_rate == 0.0


def test_generate_insight_with_outcomes() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    learner.record_outcome(project_id="p1", outcome_type="build_success", score=0.8)
    learner.record_outcome(project_id="p1", outcome_type="revenue_detected", score=0.9)
    learner.record_outcome(project_id="p2", outcome_type="build_failure", score=0.2)
    insight = learner.generate_insight()
    assert insight.total_signals == 3
    assert insight.success_rate > 0.5
    assert insight.top_success_pattern is not None


def test_pricing_performance_tracked() -> None:
    store = MemoryStore()
    learner = AutoLearner(memory_store=store)
    learner.record_outcome(
        project_id="p1", outcome_type="pricing_validated", score=0.8,
        metadata={"pricing_model": "subscription"},
    )
    learner.record_outcome(
        project_id="p2", outcome_type="pricing_validated", score=0.3,
        metadata={"pricing_model": "one_time"},
    )
    insight = learner.generate_insight()
    assert "subscription" in insight.pricing_performance
    assert "one_time" in insight.pricing_performance
