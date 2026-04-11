"""Tests for the business validation gate."""

from __future__ import annotations


from app.reasoning.validate_business_gate import (
    GateDecision,
    validate_business_gate,
)


class TestValidateBusinessGate:
    """Tests for validate_business_gate function."""

    def test_pass_with_all_fields(self) -> None:
        result = validate_business_gate(
            idea_text="SaaS tool for developers",
            problem="Developers waste time on repetitive tasks",
            target_user="Software developers",
            monetization_model="subscription",
            competition_level="low",
            differentiation="AI-powered automation with unique algorithms",
        )
        assert result.decision == GateDecision.PASS
        assert result.demand_valid is True
        assert result.monetization_valid is True
        assert not result.blocking_reasons

    def test_reject_no_demand(self) -> None:
        result = validate_business_gate(
            idea_text="Some random thing",
            problem="",
            target_user="",
            monetization_model="subscription",
        )
        assert result.decision == GateDecision.REJECT
        assert result.demand_valid is False
        assert any("demand" in r.lower() for r in result.blocking_reasons)

    def test_reject_no_monetization(self) -> None:
        result = validate_business_gate(
            idea_text="Tool for developers",
            problem="Developers waste time",
            target_user="Developers",
            monetization_model="",
        )
        assert result.decision == GateDecision.REJECT
        assert result.monetization_valid is False
        assert any("monetization" in r.lower() for r in result.blocking_reasons)

    def test_reject_high_saturation_no_differentiation(self) -> None:
        result = validate_business_gate(
            idea_text="Another project management tool with subscription model",
            problem="Project management is hard for users",
            target_user="Business teams",
            monetization_model="subscription",
            competition_level="high",
            differentiation="",
        )
        assert result.decision == GateDecision.REJECT
        assert any("saturation" in r.lower() for r in result.blocking_reasons)

    def test_pass_high_saturation_with_differentiation(self) -> None:
        result = validate_business_gate(
            idea_text="Project management tool with subscription model",
            problem="Project management is hard for users",
            target_user="Business teams",
            monetization_model="subscription",
            competition_level="high",
            differentiation="First AI-native PM tool with autonomous task allocation",
        )
        assert result.decision == GateDecision.PASS
        assert result.saturation_ok is True

    def test_demand_detected_from_text(self) -> None:
        result = validate_business_gate(
            idea_text="There is strong demand from customers for this subscription service",
            problem="People struggle with managing finances",
            target_user="",
        )
        assert result.demand_valid is True

    def test_monetization_detected_from_text(self) -> None:
        result = validate_business_gate(
            idea_text="Freemium model with premium tier pricing",
            problem="Users need better analytics",
            target_user="Data analysts",
        )
        assert result.monetization_valid is True

    def test_empty_idea_rejects(self) -> None:
        result = validate_business_gate(
            idea_text="",
            problem="",
            target_user="",
        )
        assert result.decision == GateDecision.REJECT

    def test_reasons_populated_on_pass(self) -> None:
        result = validate_business_gate(
            idea_text="SaaS subscription tool",
            problem="Users waste time on boring tasks",
            target_user="Developers",
            monetization_model="subscription",
        )
        assert len(result.reasons) >= 2

    def test_saturation_text_detection(self) -> None:
        result = validate_business_gate(
            idea_text="The market is crowded and saturated with subscription tools",
            problem="Users need better tools",
            target_user="Developers",
            monetization_model="subscription",
            differentiation="",
        )
        assert result.decision == GateDecision.REJECT
