"""Tests for the deterministic RevenueOptimizerAgent."""

from app.agents.revenue_optimizer import RevenueOptimizationResult, RevenueOptimizerAgent


def _agent() -> RevenueOptimizerAgent:
    return RevenueOptimizerAgent()


# ---------------------------------------------------------------------------
# Funnel analysis
# ---------------------------------------------------------------------------


def test_funnel_analysis_correct_rates() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 100, "conversions": 30, "revenue": 1500.0}
    )
    assert result.funnel_analysis["visit_to_click_pct"] == 10.0
    assert result.funnel_analysis["click_to_conversion_pct"] == 30.0
    assert result.funnel_analysis["visit_to_conversion_pct"] == 3.0
    assert result.funnel_analysis["revenue_per_conversion"] == 50.0


def test_funnel_analysis_zero_division_safe() -> None:
    result = _agent().optimize(analytics={"visits": 0, "clicks": 0, "conversions": 0, "revenue": 0})
    fa = result.funnel_analysis
    assert fa["visit_to_click_pct"] == 0.0
    assert fa["visit_to_conversion_pct"] == 0.0
    assert fa["revenue_per_conversion"] == 0.0


def test_funnel_analysis_zero_clicks() -> None:
    result = _agent().optimize(analytics={"visits": 500, "clicks": 0, "conversions": 0, "revenue": 0})
    assert result.funnel_analysis["visit_to_click_pct"] == 0.0
    assert result.funnel_analysis["click_to_conversion_pct"] == 0.0


# ---------------------------------------------------------------------------
# Pricing recommendations (conversion < 1%)
# ---------------------------------------------------------------------------


def test_low_conversion_recommends_cta_test() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 50, "conversions": 5, "revenue": 100.0},
        current_pricing={"model": "subscription", "price": 49},
    )
    # 5/1000 = 0.5% → below 1%
    assert result.funnel_analysis["visit_to_conversion_pct"] == 0.5
    assert "cta" in result.pricing_recommendation.lower() or "free trial" in result.pricing_recommendation.lower()
    assert result.estimated_revenue_uplift_pct == 15.0
    assert "CTA" in result.priority_action or "optimis" in result.priority_action.lower()


def test_low_conversion_suggests_cta_ab_tests() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 50, "conversions": 5, "revenue": 100.0}
    )
    tests_lower = [t.lower() for t in result.suggested_tests]
    assert any("cta" in t or "headline" in t for t in tests_lower)


# ---------------------------------------------------------------------------
# Pricing recommendations (conversion 1–3%)
# ---------------------------------------------------------------------------


def test_mid_conversion_recommends_pricing_test_high_price() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 200, "conversions": 15, "revenue": 2250.0},
        current_pricing={"model": "subscription", "price": 149},
    )
    # 15/1000 = 1.5%
    assert 1.0 <= result.funnel_analysis["visit_to_conversion_pct"] < 3.0
    assert "lower" in result.pricing_recommendation.lower() or "29" in result.pricing_recommendation


def test_mid_conversion_recommends_increasing_low_price() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 200, "conversions": 15, "revenue": 150.0},
        current_pricing={"model": "subscription", "price": 10},
    )
    assert "undervaluing" in result.pricing_recommendation.lower() or "29" in result.pricing_recommendation


def test_mid_conversion_no_price_suggests_annual() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 200, "conversions": 20, "revenue": 980.0},
        current_pricing={"model": "subscription", "price": 49},
    )
    # 20/1000 = 2%
    assert "annual" in result.pricing_recommendation.lower() or "annual" in " ".join(result.suggested_tests).lower()
    assert result.estimated_revenue_uplift_pct == 20.0


# ---------------------------------------------------------------------------
# Pricing recommendations (conversion > 3%)
# ---------------------------------------------------------------------------


def test_high_conversion_recommends_scale_distribution() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 300, "conversions": 50, "revenue": 5000.0},
        current_pricing={"model": "subscription", "price": 100},
    )
    # 50/1000 = 5%
    assert result.funnel_analysis["visit_to_conversion_pct"] == 5.0
    assert "scale" in result.pricing_recommendation.lower() or "distribution" in result.pricing_recommendation.lower()
    assert result.estimated_revenue_uplift_pct == 35.0
    assert "scale" in result.priority_action.lower() or "distribution" in result.priority_action.lower()


def test_high_conversion_suggests_enterprise_tier() -> None:
    result = _agent().optimize(
        analytics={"visits": 500, "clicks": 200, "conversions": 25, "revenue": 2500.0}
    )
    # 25/500 = 5%
    tests_lower = [t.lower() for t in result.suggested_tests]
    assert any("enterprise" in t or "referral" in t or "upsell" in t for t in tests_lower)


# ---------------------------------------------------------------------------
# Suggested tests
# ---------------------------------------------------------------------------


def test_low_click_rate_adds_landing_page_test() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 50, "conversions": 3, "revenue": 150.0}
    )
    # visit_to_click = 5% < 10% → should add landing page test
    tests_lower = [t.lower() for t in result.suggested_tests]
    assert any("landing page" in t for t in tests_lower)


def test_suggested_tests_non_empty() -> None:
    result = _agent().optimize(
        analytics={"visits": 1000, "clicks": 100, "conversions": 10, "revenue": 500.0}
    )
    assert len(result.suggested_tests) >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_missing_analytics_keys_handled() -> None:
    result = _agent().optimize(analytics={})
    assert isinstance(result, RevenueOptimizationResult)
    assert result.estimated_revenue_uplift_pct >= 0.0


def test_none_pricing_handled() -> None:
    result = _agent().optimize(
        analytics={"visits": 100, "clicks": 10, "conversions": 1, "revenue": 50.0},
        current_pricing=None,
    )
    assert isinstance(result, RevenueOptimizationResult)


def test_result_is_pydantic_model() -> None:
    result = _agent().optimize(
        analytics={"visits": 100, "clicks": 10, "conversions": 2, "revenue": 100.0}
    )
    assert isinstance(result, RevenueOptimizationResult)
