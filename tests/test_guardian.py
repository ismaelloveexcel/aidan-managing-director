"""Tests for deterministic guardian review logic."""

from app.agents.guardian import GuardianAgent


def test_guardian_approves_clean_input() -> None:
    agent = GuardianAgent()
    result = agent.review(
        idea_input={
            "title": "Focused MVP",
            "mvp_scope": ["Landing page", "CTA endpoint"],
            "pricing_hint": "Subscription $49/month",
            "target_user": "freelancer designers",
            "problem": "manual proposal workflows are slow",
            "solution": "niche workflow automation for freelancers",
        },
        validation_score=0.9,
        monetization_model="subscription",
    )
    assert result.decision == "APPROVE"
    assert result.risk_flags == []


def test_guardian_flags_overlap_risk() -> None:
    agent = GuardianAgent()
    result = agent.review(
        idea_input={
            "title": "AI SaaS assistant dashboard platform",
            "mvp_scope": ["Landing page", "CTA endpoint"],
            "pricing_hint": "Subscription $39/month",
            "target_user": "all users",
            "problem": "generic productivity tasks",
            "solution": "generic assistant for everyone",
        },
        validation_score=0.9,
        monetization_model="subscription",
    )
    assert result.decision == "FLAG"
    assert "high_saturation_no_differentiation" in result.risk_flags


def test_guardian_blocks_oversized_scope() -> None:
    agent = GuardianAgent()
    result = agent.review(
        idea_input={
            "title": "Oversized MVP",
            "mvp_scope": ["a", "b", "c", "d", "e", "f", "g", "h", "i"],
            "pricing_hint": "Monthly subscription",
        },
        validation_score=0.8,
        monetization_model="subscription",
    )
    assert result.decision == "BLOCK"
    assert "scope_too_large" in result.risk_flags
