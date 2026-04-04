"""Tests for the fast decision engine."""

from app.feedback.fast_decision import FastDecision, fast_decide, reset_tracker


def setup_function() -> None:
    """Reset iteration tracker before each test."""
    reset_tracker()


def test_revenue_detected_scales() -> None:
    result = fast_decide(project_id="p1", visits=50, signups=5, revenue=10.0)
    assert result.action == "SCALE"
    assert result.confidence > 0.9


def test_visits_no_conversions_kills() -> None:
    result = fast_decide(project_id="p1", visits=100, signups=0, revenue=0.0)
    assert result.action == "KILL"


def test_interest_only_iterates_once() -> None:
    result = fast_decide(project_id="p1", visits=150, signups=10, revenue=0.0)
    assert result.action == "ITERATE"
    assert result.iteration_count == 1
    # Second call should KILL
    result2 = fast_decide(project_id="p1", visits=150, signups=10, revenue=0.0)
    assert result2.action == "KILL"


def test_no_distribution_suggests_change() -> None:
    result = fast_decide(
        project_id="p1", visits=0, signups=0, revenue=0.0, has_distribution=False,
    )
    assert result.action == "CHANGE_DISTRIBUTION"


def test_distribution_changed_still_no_traffic_kills() -> None:
    result = fast_decide(
        project_id="p1", visits=0, signups=0, revenue=0.0,
        has_distribution=True, distribution_changed=True,
    )
    assert result.action == "KILL"


def test_monitor_default() -> None:
    result = fast_decide(project_id="p1", visits=50, signups=2, revenue=0.0)
    assert result.action == "MONITOR"


def test_max_one_iteration() -> None:
    """Verify strict max-1 iteration limit."""
    fast_decide(project_id="p1", visits=5, signups=0, revenue=0.0)
    result = fast_decide(project_id="p1", visits=5, signups=0, revenue=0.0)
    assert result.can_iterate is False
