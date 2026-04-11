"""Tests for the distribution engine."""

from __future__ import annotations


from app.planning.distribution_engine import (
    DistributionDecision,
    generate_distribution,
)


class TestDistributionEngine:
    """Tests for generate_distribution function."""

    def test_generate_developer_distribution(self) -> None:
        result = generate_distribution(
            title="DevTool",
            problem="Slow development cycles",
            target_user="Software developers",
        )
        assert result.decision == DistributionDecision.GENERATED
        assert result.primary_channel
        assert result.acquisition_method
        assert result.first_10_users_plan
        assert result.messaging
        assert len(result.execution_steps) > 0

    def test_generate_founder_distribution(self) -> None:
        result = generate_distribution(
            title="FounderKit",
            problem="Startup chaos",
            target_user="Startup founders",
        )
        assert result.decision == DistributionDecision.GENERATED
        assert "linkedin" in result.primary_channel.lower()

    def test_generate_business_distribution(self) -> None:
        result = generate_distribution(
            title="BizTool",
            problem="B2B inefficiency",
            target_user="Business teams and enterprises",
        )
        assert result.decision == DistributionDecision.GENERATED
        assert "email" in result.primary_channel.lower() or "linkedin" in result.primary_channel.lower()

    def test_generate_freelancer_distribution(self) -> None:
        result = generate_distribution(
            title="FreelanceHelper",
            problem="Client management chaos",
            target_user="Freelancers",
        )
        assert result.decision == DistributionDecision.GENERATED

    def test_generate_default_distribution(self) -> None:
        result = generate_distribution(
            title="GenericTool",
            problem="General problem",
            target_user="Researchers",
        )
        assert result.decision == DistributionDecision.GENERATED
        assert result.primary_channel  # Should use default channel

    def test_reject_missing_title(self) -> None:
        result = generate_distribution(
            title="",
            problem="A problem",
            target_user="Users",
        )
        assert result.decision == DistributionDecision.REJECTED
        assert "title" in result.rejection_reason.lower()

    def test_reject_missing_target_user(self) -> None:
        result = generate_distribution(
            title="MyProduct",
            problem="A problem",
            target_user="",
        )
        assert result.decision == DistributionDecision.REJECTED
        assert "target" in result.rejection_reason.lower()

    def test_messaging_contains_problem(self) -> None:
        result = generate_distribution(
            title="TaskFlow",
            problem="wasting time on manual tasks",
            target_user="Developers",
        )
        assert "wasting time" in result.messaging.lower() or "TaskFlow" in result.messaging

    def test_estimated_days_reasonable(self) -> None:
        result = generate_distribution(
            title="Test",
            problem="Test",
            target_user="Developers",
        )
        assert 1 <= result.estimated_days <= 30

    def test_execution_steps_are_actionable(self) -> None:
        result = generate_distribution(
            title="Test",
            problem="Test",
            target_user="Startup founders",
        )
        assert len(result.execution_steps) >= 3
        for step in result.execution_steps:
            assert len(step) > 10  # Steps should be descriptive
