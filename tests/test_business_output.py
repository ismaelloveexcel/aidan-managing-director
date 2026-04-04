"""Tests for the business output engine."""

from app.planning.business_output import generate_business_output


def test_generates_complete_output() -> None:
    result = generate_business_output(
        project_id="prj-001",
        idea_id="idea-001",
        idea={"title": "TestApp", "problem": "slow process", "target_user": "devs", "solution": "automate it"},
        evaluation={"total_score": 8.5, "breakdown": {"demand": 2.0}, "decision": "APPROVE"},
        business_package={
            "offer": "TestApp for devs",
            "pricing_model": "subscription",
            "price_range": "$29-$99/month",
            "landing_page": {"headline": "H1", "subheadline": "H2", "cta": "Start now"},
            "gtm_strategy": ["SEO", "LinkedIn"],
        },
    )
    assert result["project_id"] == "prj-001"
    assert result["total_score"] == 8.5
    assert result["pricing_model"] == "subscription"
    assert result["status"] == "generated"


def test_optional_deployment() -> None:
    result = generate_business_output(
        project_id="prj-002",
        idea_id="idea-002",
        idea={"title": "Test", "problem": "p", "target_user": "u", "solution": "s"},
        evaluation={"total_score": 7.0, "decision": "HOLD"},
        business_package={"offer": "x", "pricing_model": "one_time", "price_range": "$149"},
        deployment={"repo_url": "https://github.com/test/repo", "deploy_url": "https://example.com"},
    )
    assert result["repo_url"] == "https://github.com/test/repo"
    assert result["deploy_url"] == "https://example.com"


def test_schema_version() -> None:
    result = generate_business_output(
        project_id="prj-003",
        idea_id="idea-003",
        idea={"title": "T", "problem": "p", "target_user": "u", "solution": "s"},
        evaluation={"total_score": 5.0, "decision": "REJECT"},
        business_package={"offer": "o", "pricing_model": "pm", "price_range": "pr"},
    )
    assert result["schema_version"] == "1.0"
