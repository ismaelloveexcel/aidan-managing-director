"""Tests for the analytics tracker."""

from __future__ import annotations

import pytest

from app.feedback.analytics_tracker import (
    AnalyticsTracker,
    TrackerDecision,
)


class TestAnalyticsTracker:
    """Tests for AnalyticsTracker."""

    def test_record_visit(self) -> None:
        tracker = AnalyticsTracker()
        snapshot = tracker.record_event("proj-1", event_type="visit")
        assert snapshot.visits == 1
        assert snapshot.clicks == 0

    def test_record_click(self) -> None:
        tracker = AnalyticsTracker()
        snapshot = tracker.record_event("proj-1", event_type="click")
        assert snapshot.clicks == 1

    def test_record_conversion_with_revenue(self) -> None:
        tracker = AnalyticsTracker()
        snapshot = tracker.record_event("proj-1", event_type="conversion", value=49.99)
        assert snapshot.conversions == 1
        assert snapshot.revenue == 49.99

    def test_record_revenue_event(self) -> None:
        tracker = AnalyticsTracker()
        snapshot = tracker.record_event("proj-1", event_type="revenue", value=100.0)
        assert snapshot.revenue == 100.0

    def test_cumulative_events(self) -> None:
        tracker = AnalyticsTracker()
        tracker.record_event("proj-1", event_type="visit")
        tracker.record_event("proj-1", event_type="visit")
        tracker.record_event("proj-1", event_type="click")
        snapshot = tracker.record_event("proj-1", event_type="signup")
        assert snapshot.visits == 2
        assert snapshot.clicks == 1
        assert snapshot.signups == 1

    def test_get_latest(self) -> None:
        tracker = AnalyticsTracker()
        tracker.record_event("proj-1", event_type="visit")
        latest = tracker.get_latest("proj-1")
        assert latest is not None
        assert latest.visits == 1

    def test_get_latest_none_for_unknown(self) -> None:
        tracker = AnalyticsTracker()
        assert tracker.get_latest("unknown") is None

    def test_get_history(self) -> None:
        tracker = AnalyticsTracker()
        tracker.record_event("proj-1", event_type="visit")
        tracker.record_event("proj-1", event_type="click")
        history = tracker.get_history("proj-1")
        assert len(history) == 2

    def test_decide_monitor_no_data(self) -> None:
        tracker = AnalyticsTracker()
        decision = tracker.decide("unknown")
        assert decision.decision == TrackerDecision.MONITOR
        assert decision.confidence < 0.5

    def test_decide_scale_with_revenue(self) -> None:
        tracker = AnalyticsTracker()
        for _ in range(50):
            tracker.record_event("proj-1", event_type="visit")
        for _ in range(3):
            tracker.record_event("proj-1", event_type="conversion", value=49.0)
        decision = tracker.decide("proj-1")
        assert decision.decision == TrackerDecision.SCALE

    def test_decide_kill_no_traction(self) -> None:
        tracker = AnalyticsTracker()
        for _ in range(100):
            tracker.record_event("proj-1", event_type="visit")
        decision = tracker.decide("proj-1")
        assert decision.decision == TrackerDecision.KILL

    def test_decide_iterate_interest_no_conversion(self) -> None:
        tracker = AnalyticsTracker()
        for _ in range(60):
            tracker.record_event("proj-1", event_type="visit")
        for _ in range(10):
            tracker.record_event("proj-1", event_type="click")
        decision = tracker.decide("proj-1")
        assert decision.decision == TrackerDecision.ITERATE

    def test_decide_monitor_insufficient_data(self) -> None:
        tracker = AnalyticsTracker()
        for _ in range(5):
            tracker.record_event("proj-1", event_type="visit")
        decision = tracker.decide("proj-1")
        assert decision.decision == TrackerDecision.MONITOR

    def test_reset(self) -> None:
        tracker = AnalyticsTracker()
        tracker.record_event("proj-1", event_type="visit")
        tracker.reset("proj-1")
        assert tracker.get_latest("proj-1") is None

    def test_negative_revenue_clamped(self) -> None:
        tracker = AnalyticsTracker()
        snapshot = tracker.record_event("proj-1", event_type="revenue", value=-50.0)
        assert snapshot.revenue == 0.0

    def test_decision_metrics_populated(self) -> None:
        tracker = AnalyticsTracker()
        tracker.record_event("proj-1", event_type="visit")
        decision = tracker.decide("proj-1")
        assert "visits" in decision.metrics
        assert "revenue" in decision.metrics
