"""Tests for the revenue intelligence layer.

Covers:
- Payment signal integration (decision policy)
- User feedback intelligence (mapping + memory storage)
- Auto-learner analysis
- Fast decision engine
- Business output generation
- Revenue route endpoints
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.dependencies import get_feedback_service, get_memory_store, get_portfolio_repository
from app.feedback.decision_policy import decide
from app.feedback.fast_decision import FastDecisionInput, fast_decide
from app.feedback.models import (
    FEEDBACK_ACTION_MAP,
    UserFeedbackAction,
    UserFeedbackRequest,
    UserFeedbackType,
)
from app.feedback.service import FeedbackService
from app.memory.auto_learner import AutoLearner
from app.memory.store import LearningSignal, MemoryStore
from app.planning.business_output import build_business_output
from main import app

client = TestClient(app)


# ======================================================================
# Payment signal decision policy
# ======================================================================


class TestPaymentSignalDecisionPolicy:
    """Test payment-aware decision rules."""

    def test_payment_success_triggers_scale(self) -> None:
        result = decide(visits=10, conversion_rate=0.0, revenue=0.0, payment_success=True)
        assert result.decision == "scale_candidate"
        assert result.confidence == 0.95

    def test_payment_attempted_no_success_triggers_iterate_pricing(self) -> None:
        result = decide(
            visits=50,
            conversion_rate=0.01,
            revenue=0.0,
            payment_attempted=True,
            payment_success=False,
        )
        assert result.decision == "iterate_pricing"
        assert "pricing" in result.next_action.lower() or "offer" in result.next_action.lower()

    def test_payment_success_overrides_kill_candidate(self) -> None:
        """Even with kill-candidate metrics, payment success wins."""
        result = decide(
            visits=300,
            conversion_rate=0.005,
            revenue=0.0,
            payment_success=True,
        )
        assert result.decision == "scale_candidate"

    def test_high_traffic_payment_attempted_no_success(self) -> None:
        result = decide(
            visits=150,
            conversion_rate=0.01,
            revenue=0.0,
            payment_attempted=True,
            payment_success=False,
        )
        assert result.decision == "iterate_pricing"

    def test_original_kill_still_works_without_payment(self) -> None:
        result = decide(visits=300, conversion_rate=0.005, revenue=0.0)
        assert result.decision == "kill_candidate"

    def test_original_scale_still_works_without_payment(self) -> None:
        result = decide(visits=250, conversion_rate=0.05, revenue=10.0)
        assert result.decision == "scale_candidate"

    def test_original_revise_still_works(self) -> None:
        result = decide(visits=250, conversion_rate=0.02, revenue=0.0)
        assert result.decision == "revise_candidate"

    def test_original_monitor_still_works(self) -> None:
        result = decide(visits=100, conversion_rate=0.02, revenue=0.0)
        assert result.decision == "monitor"


# ======================================================================
# Feedback decision policy
# ======================================================================


class TestFeedbackDecisionPolicy:
    """Test user-feedback overrides in decision policy."""

    def test_too_expensive_triggers_iterate_pricing(self) -> None:
        result = decide(
            visits=0,
            conversion_rate=0.0,
            revenue=0.0,
            feedback=UserFeedbackType.TOO_EXPENSIVE,
        )
        assert result.decision == "iterate_pricing"

    def test_not_clear_triggers_revise_messaging(self) -> None:
        result = decide(
            visits=0,
            conversion_rate=0.0,
            revenue=0.0,
            feedback=UserFeedbackType.NOT_CLEAR,
        )
        assert result.decision == "revise_messaging"

    def test_not_needed_triggers_kill(self) -> None:
        result = decide(
            visits=0,
            conversion_rate=0.0,
            revenue=0.0,
            feedback=UserFeedbackType.NOT_NEEDED,
        )
        assert result.decision == "kill_candidate"

    def test_payment_success_overrides_feedback(self) -> None:
        """Payment success has highest priority."""
        result = decide(
            visits=0,
            conversion_rate=0.0,
            revenue=0.0,
            payment_success=True,
            feedback=UserFeedbackType.TOO_EXPENSIVE,
        )
        assert result.decision == "scale_candidate"


# ======================================================================
# Feedback action mapping
# ======================================================================


class TestFeedbackActionMapping:
    """Test deterministic feedback-to-action mapping."""

    def test_too_expensive_maps_to_adjust_pricing(self) -> None:
        assert FEEDBACK_ACTION_MAP[UserFeedbackType.TOO_EXPENSIVE] == UserFeedbackAction.ADJUST_PRICING

    def test_not_clear_maps_to_improve_messaging(self) -> None:
        assert FEEDBACK_ACTION_MAP[UserFeedbackType.NOT_CLEAR] == UserFeedbackAction.IMPROVE_MESSAGING

    def test_not_needed_maps_to_downgrade(self) -> None:
        assert FEEDBACK_ACTION_MAP[UserFeedbackType.NOT_NEEDED] == UserFeedbackAction.DOWNGRADE_IDEA_SCORE

    def test_other_maps_to_log(self) -> None:
        assert FEEDBACK_ACTION_MAP[UserFeedbackType.OTHER] == UserFeedbackAction.LOG_OTHER


# ======================================================================
# FeedbackService – user feedback processing
# ======================================================================


class TestFeedbackServiceUserFeedback:
    """Test FeedbackService.process_user_feedback."""

    def test_process_feedback_returns_mapped_action(self) -> None:
        mem = MemoryStore()
        repo = get_portfolio_repository()
        repo.reset()
        svc = FeedbackService(repository=repo, memory_store=mem)

        req = UserFeedbackRequest(
            project_id="proj-1",
            feedback_type=UserFeedbackType.TOO_EXPENSIVE,
            detail="Price is 2x the competition",
        )
        resp = svc.process_user_feedback(req)
        assert resp.mapped_action == UserFeedbackAction.ADJUST_PRICING
        assert resp.project_id == "proj-1"
        assert resp.detail == "Price is 2x the competition"

    def test_feedback_stored_in_memory(self) -> None:
        mem = MemoryStore()
        repo = get_portfolio_repository()
        repo.reset()
        svc = FeedbackService(repository=repo, memory_store=mem)

        svc.process_user_feedback(
            UserFeedbackRequest(
                project_id="proj-2",
                feedback_type=UserFeedbackType.NOT_CLEAR,
            ),
        )
        signals = mem.get_project_signals("proj-2")
        assert len(signals) == 1
        assert signals[0].signal_type == "user_feedback_not_clear"

        events = mem.recent_events(limit=5)
        assert any(e["event_type"] == "user_feedback" for e in events)


# ======================================================================
# FeedbackService – payment signal memory recording
# ======================================================================


class TestFeedbackServicePaymentSignals:
    """Test that payment signals are recorded in memory."""

    def test_payment_attempted_recorded(self) -> None:
        mem = MemoryStore()
        repo = get_portfolio_repository()
        repo.reset()
        project = repo.create_project(name="pay-test", description="test")
        svc = FeedbackService(repository=repo, memory_store=mem)

        from app.feedback.models import MetricsIngestRequest

        svc.ingest_metrics(
            MetricsIngestRequest(
                project_id=project.project_id,
                visits=100,
                signups=5,
                revenue=0,
                timestamp="2026-04-04T00:00:00+00:00",
                payment_attempted=True,
                payment_success=False,
            ),
        )
        signals = mem.get_project_signals(project.project_id)
        types = [s.signal_type for s in signals]
        assert "payment_attempted" in types

    def test_payment_success_recorded(self) -> None:
        mem = MemoryStore()
        repo = get_portfolio_repository()
        repo.reset()
        project = repo.create_project(name="pay-ok", description="test")
        svc = FeedbackService(repository=repo, memory_store=mem)

        from app.feedback.models import MetricsIngestRequest

        svc.ingest_metrics(
            MetricsIngestRequest(
                project_id=project.project_id,
                visits=100,
                signups=5,
                revenue=50,
                timestamp="2026-04-04T00:00:00+00:00",
                payment_attempted=True,
                payment_success=True,
                revenue_amount=49.99,
            ),
        )
        signals = mem.get_project_signals(project.project_id)
        types = [s.signal_type for s in signals]
        assert "payment_success" in types
        assert "payment_attempted" in types


# ======================================================================
# Auto-learner
# ======================================================================


class TestAutoLearner:
    """Test auto-learner analysis."""

    def test_empty_signals_returns_defaults(self) -> None:
        mem = MemoryStore()
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-empty")
        assert report.total_signals == 0
        assert report.pricing_objection_count == 0
        assert report.scoring_weight_updates == []
        assert report.pricing_recommendation is None
        assert report.prioritization_adjustment == "hold"

    def test_pricing_objections_trigger_reduce(self) -> None:
        mem = MemoryStore()
        for _ in range(4):
            mem.record_signal(
                LearningSignal(
                    project_id="proj-price",
                    signal_type="user_feedback_too_expensive",
                    score=0.3,
                ),
            )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-price")
        assert report.pricing_objection_count == 4
        assert report.pricing_recommendation is not None
        assert report.pricing_recommendation.direction == "reduce"

    def test_payment_attempted_no_success_triggers_reduce(self) -> None:
        mem = MemoryStore()
        for _ in range(3):
            mem.record_signal(
                LearningSignal(
                    project_id="proj-pay",
                    signal_type="payment_attempted",
                    score=0.5,
                ),
            )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-pay")
        assert report.pricing_recommendation is not None
        assert report.pricing_recommendation.direction == "reduce"

    def test_payment_success_triggers_hold(self) -> None:
        mem = MemoryStore()
        mem.record_signal(
            LearningSignal(
                project_id="proj-ok",
                signal_type="payment_success",
                score=1.0,
            ),
        )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-ok")
        assert report.pricing_recommendation is not None
        assert report.pricing_recommendation.direction == "hold"

    def test_scoring_weight_increase_for_pricing(self) -> None:
        mem = MemoryStore()
        # 4 out of 10 signals are pricing => 40% >= 30% threshold
        for _ in range(4):
            mem.record_signal(
                LearningSignal(project_id="proj-w", signal_type="user_feedback_too_expensive", score=0.3),
            )
        for _ in range(6):
            mem.record_signal(
                LearningSignal(project_id="proj-w", signal_type="other_signal", score=0.5),
            )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-w")
        factors = [u.factor for u in report.scoring_weight_updates]
        assert "pricing_fit" in factors

    def test_not_needed_lowers_demand_weight(self) -> None:
        mem = MemoryStore()
        # 5 out of 10 signals are not_needed => 50% >= 40% threshold
        for _ in range(5):
            mem.record_signal(
                LearningSignal(project_id="proj-nn", signal_type="user_feedback_not_needed", score=0.1),
            )
        for _ in range(5):
            mem.record_signal(
                LearningSignal(project_id="proj-nn", signal_type="other", score=0.5),
            )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-nn")
        factors = [u.factor for u in report.scoring_weight_updates]
        assert "market_demand" in factors
        assert report.prioritization_adjustment == "lower"

    def test_conversion_blockers_identified(self) -> None:
        mem = MemoryStore()
        for _ in range(3):
            mem.record_signal(
                LearningSignal(project_id="proj-b", signal_type="user_feedback_not_clear", score=0.4),
            )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-b")
        blocker_types = [b.blocker_type for b in report.conversion_blockers]
        assert "messaging" in blocker_types

    def test_payment_success_raises_prioritization(self) -> None:
        mem = MemoryStore()
        mem.record_signal(
            LearningSignal(project_id="proj-up", signal_type="payment_success", score=1.0),
        )
        learner = AutoLearner(memory_store=mem)
        report = learner.analyse("proj-up")
        assert report.prioritization_adjustment == "raise"


# ======================================================================
# Fast decision engine
# ======================================================================


class TestFastDecisionEngine:
    """Test fast decision engine with payment + feedback."""

    def test_scale_on_payment_success(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p1",
                visits=10,
                conversion_rate=0.0,
                revenue=0.0,
                payment_success=True,
            ),
        )
        assert result.action == "scale"
        assert not result.iteration_applied
        assert not result.max_iterations_reached

    def test_iterate_on_payment_attempted_no_success(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p2",
                visits=50,
                conversion_rate=0.01,
                revenue=0.0,
                payment_attempted=True,
            ),
        )
        assert result.action == "iterate"
        assert result.iteration_applied

    def test_kill_on_not_needed(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p3",
                visits=0,
                conversion_rate=0.0,
                revenue=0.0,
                feedback=UserFeedbackType.NOT_NEEDED,
            ),
        )
        assert result.action == "kill"

    def test_revise_messaging_on_not_clear(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p4",
                visits=0,
                conversion_rate=0.0,
                revenue=0.0,
                feedback=UserFeedbackType.NOT_CLEAR,
            ),
        )
        assert result.action == "revise_messaging"

    def test_max_iteration_enforced(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p5",
                visits=50,
                conversion_rate=0.01,
                revenue=0.0,
                payment_attempted=True,
                iteration_count=1,
            ),
        )
        assert result.max_iterations_reached
        assert result.action == "kill"
        assert not result.iteration_applied

    def test_max_iteration_revise_messaging_becomes_monitor(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p6",
                visits=0,
                conversion_rate=0.0,
                revenue=0.0,
                feedback=UserFeedbackType.NOT_CLEAR,
                iteration_count=1,
            ),
        )
        assert result.max_iterations_reached
        assert result.action == "monitor"

    def test_monitor_default(self) -> None:
        result = fast_decide(
            FastDecisionInput(
                project_id="p7",
                visits=50,
                conversion_rate=0.02,
                revenue=0.0,
            ),
        )
        assert result.action == "monitor"


# ======================================================================
# Business output
# ======================================================================


class TestBusinessOutput:
    """Test business output generation."""

    def test_default_output(self) -> None:
        output = build_business_output(project_id="proj-1")
        assert output.project_id == "proj-1"
        assert output.pricing_strategy == "default"
        assert output.conversion_status == "unknown"
        assert output.feedback_summary.total_feedback_count == 0

    def test_feedback_summary_aggregation(self) -> None:
        output = build_business_output(
            project_id="proj-2",
            feedback_counts={
                "user_feedback_too_expensive": 5,
                "user_feedback_not_clear": 2,
                "user_feedback_not_needed": 1,
            },
        )
        assert output.feedback_summary.too_expensive_count == 5
        assert output.feedback_summary.not_clear_count == 2
        assert output.feedback_summary.not_needed_count == 1
        assert output.feedback_summary.total_feedback_count == 8
        assert output.feedback_summary.dominant_feedback == "too_expensive"

    def test_pricing_strategy_auto_reduce(self) -> None:
        output = build_business_output(
            project_id="proj-3",
            feedback_counts={"user_feedback_too_expensive": 5},
        )
        assert output.pricing_strategy == "reduce"

    def test_payment_link_included(self) -> None:
        output = build_business_output(
            project_id="proj-4",
            payment_link="https://pay.example.com/proj-4",
        )
        assert output.payment_link == "https://pay.example.com/proj-4"

    def test_conversion_status_passed_through(self) -> None:
        output = build_business_output(
            project_id="proj-5",
            conversion_status="converting",
        )
        assert output.conversion_status == "converting"


# ======================================================================
# Route tests
# ======================================================================


def _make_project() -> str:
    repo = get_portfolio_repository()
    project = repo.create_project(name="rev-test", description="revenue test")
    return project.project_id


class TestRevenueRoutes:
    """Test revenue intelligence API endpoints."""

    def test_learning_report_endpoint(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        mem = get_memory_store()
        mem.reset()

        resp = client.get("/revenue/projects/unknown/learning-report")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_signals"] == 0

    def test_fast_decision_endpoint(self) -> None:
        resp = client.post(
            "/revenue/fast-decision",
            json={
                "project_id": "fast-1",
                "visits": 200,
                "conversion_rate": 0.01,
                "revenue": 0.0,
                "payment_attempted": True,
                "payment_success": False,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "iterate"
        assert body["project_id"] == "fast-1"

    def test_business_output_endpoint(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        mem = get_memory_store()
        mem.reset()
        pid = _make_project()

        resp = client.post(
            f"/revenue/projects/{pid}/business-output",
            json={
                "project_id": pid,
                "payment_link": "https://pay.example.com/test",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == pid
        assert body["payment_link"] == "https://pay.example.com/test"
        assert "feedback_summary" in body
        assert "conversion_status" in body

    def test_user_feedback_endpoint(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        mem = get_memory_store()
        mem.reset()

        resp = client.post(
            "/feedback/user-feedback",
            json={
                "project_id": "fb-1",
                "feedback_type": "too_expensive",
                "detail": "Way too pricey",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mapped_action"] == "adjust_pricing"
        assert body["feedback_type"] == "too_expensive"

    def test_metrics_ingest_with_payment_signals(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        mem = get_memory_store()
        mem.reset()
        pid = _make_project()

        resp = client.post(
            "/feedback/metrics",
            json={
                "project_id": pid,
                "visits": 150,
                "signups": 10,
                "revenue": 0,
                "currency": "USD",
                "timestamp": "2026-04-04T00:00:00+00:00",
                "payment_attempted": True,
                "payment_success": False,
                "revenue_amount": 0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["payment_attempted"] is True
        assert body["payment_success"] is False
