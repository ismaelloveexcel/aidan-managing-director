"""Tests for the offer engine."""

from __future__ import annotations


from app.planning.offer_engine import (
    OfferDecision,
    generate_offer,
)


class TestOfferEngine:
    """Tests for generate_offer function."""

    def test_generate_basic_offer(self) -> None:
        result = generate_offer(
            title="TaskFlow",
            problem="Developers waste time on repetitive tasks",
            target_user="Software developers",
            monetization_model="subscription",
        )
        assert result.decision == OfferDecision.GENERATED
        assert result.problem == "Developers waste time on repetitive tasks"
        assert result.target_customer == "Software developers"
        assert result.pricing
        assert result.pricing_model
        assert result.delivery_method
        assert result.cta

    def test_reject_missing_title(self) -> None:
        result = generate_offer(
            title="",
            problem="A problem",
            target_user="Users",
        )
        assert result.decision == OfferDecision.REJECTED
        assert "title" in result.rejection_reason.lower()

    def test_reject_missing_problem(self) -> None:
        result = generate_offer(
            title="MyProduct",
            problem="",
            target_user="Users",
        )
        assert result.decision == OfferDecision.REJECTED
        assert "problem" in result.rejection_reason.lower()

    def test_reject_missing_target_user(self) -> None:
        result = generate_offer(
            title="MyProduct",
            problem="A problem",
            target_user="",
        )
        assert result.decision == OfferDecision.REJECTED
        assert "target" in result.rejection_reason.lower()

    def test_subscription_pricing(self) -> None:
        result = generate_offer(
            title="Test",
            problem="Problem",
            target_user="Users",
            monetization_model="subscription",
        )
        assert "subscription" in result.pricing_model.lower() or "$" in result.pricing

    def test_freemium_pricing(self) -> None:
        result = generate_offer(
            title="Test",
            problem="Problem",
            target_user="Users",
            monetization_model="freemium",
        )
        assert "free" in result.pricing.lower() or "freemium" in result.pricing_model.lower()

    def test_marketplace_pricing(self) -> None:
        result = generate_offer(
            title="Test",
            problem="Problem",
            target_user="Users",
            monetization_model="marketplace",
        )
        assert "marketplace" in result.pricing_model.lower()

    def test_cta_contains_title(self) -> None:
        result = generate_offer(
            title="TaskFlow",
            problem="Wasting time",
            target_user="Developers",
        )
        assert "TaskFlow" in result.cta

    def test_value_proposition_populated(self) -> None:
        result = generate_offer(
            title="TestProduct",
            problem="Time wasted on tasks",
            target_user="Engineers",
        )
        assert result.value_proposition
        assert "TestProduct" in result.value_proposition

    def test_solution_used_as_core_offer(self) -> None:
        result = generate_offer(
            title="Test",
            problem="Problem",
            target_user="Users",
            solution="AI-powered automation platform",
        )
        assert "AI-powered automation platform" in result.core_offer

    def test_default_pricing_when_no_model(self) -> None:
        result = generate_offer(
            title="Test",
            problem="Problem",
            target_user="Users",
            monetization_model="",
        )
        assert result.decision == OfferDecision.GENERATED
        assert result.pricing  # Should have default pricing
