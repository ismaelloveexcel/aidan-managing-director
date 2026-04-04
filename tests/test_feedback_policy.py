"""Tests for deterministic feedback decision policy."""

from app.feedback.decision_policy import decide


def test_policy_kill_candidate() -> None:
    result = decide(visits=300, conversion_rate=0.005, revenue=0.0)
    assert result.decision == "kill_candidate"
    assert result.confidence > 0


def test_policy_scale_candidate() -> None:
    result = decide(visits=250, conversion_rate=0.05, revenue=10.0)
    assert result.decision == "scale_candidate"
    assert result.next_action == "Increase distribution and prioritize feature expansion."


def test_policy_revise_candidate() -> None:
    result = decide(visits=250, conversion_rate=0.02, revenue=0.0)
    assert result.decision == "revise_candidate"


def test_policy_monitor() -> None:
    result = decide(visits=50, conversion_rate=0.02, revenue=0.0)
    assert result.decision == "monitor"
