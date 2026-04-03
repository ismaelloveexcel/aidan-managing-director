"""Tests for deterministic guardian review logic."""

from app.agents.guardian import GuardianAgent


def test_guardian_approves_clean_input() -> None:
    agent = GuardianAgent()
    result = agent.review(
        idea_input={
            "title": "Focused MVP",
            "mvp_scope": ["Landing page", "CTA endpoint"],
            "pricing_hint": "Free waitlist",
        },
        validation_score=0.9,
        monetization_model="waitlist",
    )
    assert result.decision == "APPROVE"
    assert result.risk_flags == []


def test_guardian_flags_overlap_risk() -> None:
    agent = GuardianAgent()
    result = agent.review(
        idea_input={
            "title": "Copycat clone product",
            "mvp_scope": ["Landing page", "CTA endpoint"],
            "pricing_hint": "Free waitlist",
        },
        validation_score=0.9,
        monetization_model="waitlist",
    )
    assert result.decision == "FLAG"
    assert "possible_duplicate_overlap" in result.risk_flags


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
