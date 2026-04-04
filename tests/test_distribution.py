"""Tests for the distribution engine."""

from app.planning.distribution import generate_distribution_plan


def test_developer_audience() -> None:
    plan = generate_distribution_plan(
        title="DevTool Pro",
        target_user="Software developers",
        problem="slow debugging",
    )
    assert "GitHub" in plan["primary_channel"]
    assert len(plan["execution_steps"]) >= 1


def test_freelancer_audience() -> None:
    plan = generate_distribution_plan(
        title="FreelanceHelper",
        target_user="Freelancers",
        problem="invoice tracking",
    )
    assert "LinkedIn" in plan["primary_channel"]


def test_business_audience() -> None:
    plan = generate_distribution_plan(
        title="B2B Sales Tool",
        target_user="B2B sales teams",
        problem="slow pipeline management",
    )
    assert "Cold Email" in plan["primary_channel"]


def test_default_audience() -> None:
    plan = generate_distribution_plan(
        title="General Tool",
        target_user="project managers",
        problem="task overload",
    )
    assert "SEO" in plan["primary_channel"]


def test_plan_has_required_fields() -> None:
    plan = generate_distribution_plan(
        title="TestProduct",
        target_user="Founders",
        problem="no users",
    )
    assert "primary_channel" in plan
    assert "first_10_users_plan" in plan
    assert "messaging" in plan
    assert "execution_steps" in plan
    assert "estimated_days_to_first_10" in plan
