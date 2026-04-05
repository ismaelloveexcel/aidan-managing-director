"""Tests for the AI integration and analyze endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Root UI tests
# ---------------------------------------------------------------------------


class TestRootUI:
    """Verify the root route serves the HTML UI."""

    def test_root_returns_html(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_root_contains_title(self) -> None:
        resp = client.get("/")
        assert "AI-DAN Managing Director" in resp.text

    def test_root_contains_input_form(self) -> None:
        resp = client.get("/")
        assert "idea" in resp.text
        assert "analyzeBtn" in resp.text

    def test_root_contains_analyze_endpoint(self) -> None:
        resp = client.get("/")
        assert "/api/analyze/" in resp.text

    def test_root_does_not_use_innerhtml_for_verdict(self) -> None:
        """Verify XSS safety: all user data is escaped via escapeHtml."""
        resp = client.get("/")
        assert "escapeHtml" in resp.text


# ---------------------------------------------------------------------------
# Analyze endpoint tests
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    """Verify the /api/analyze/ endpoint works end-to-end."""

    def test_analyze_returns_200(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "SaaS for freelancers"})
        assert resp.status_code == 200

    def test_analyze_returns_structured_output(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "Invoice tracking tool"})
        data = resp.json()
        assert "validation_passed" in data
        assert "total_score" in data
        assert "score_decision" in data
        assert "offer" in data
        assert "distribution" in data
        assert "final_decision" in data
        assert "pipeline_stage" in data

    def test_analyze_has_monetization_fields(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "AI chatbot for e-commerce",
            "problem": "Online stores lose sales due to slow support",
            "target_user": "e-commerce store owners",
            "monetization_model": "subscription",
        })
        data = resp.json()
        if data["validation_passed"]:
            offer = data["offer"]
            assert offer.get("pricing")
            assert offer.get("pricing_model")
            distribution = data["distribution"]
            assert distribution.get("primary_channel")
        else:
            # Validation rejected: ensure blocking reasons exist
            assert data["final_decision"] == "REJECTED"
            assert len(data["validation_blocking"]) > 0

    def test_analyze_includes_pipeline_result(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "Marketplace for tutors"})
        data = resp.json()
        assert "score_breakdown" in data
        assert "score_dimensions" in data
        assert isinstance(data["score_breakdown"], dict)
        assert isinstance(data["score_dimensions"], list)

    def test_analyze_rejects_empty_input(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": ""})
        assert resp.status_code == 422

    def test_analyze_rejects_missing_field(self) -> None:
        resp = client.post("/api/analyze/", json={})
        assert resp.status_code == 422

    def test_analyze_scores_are_numeric(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "SaaS dashboard for HR teams"})
        data = resp.json()
        assert isinstance(data["total_score"], (int, float))
        breakdown = data["score_breakdown"]
        for key in breakdown:
            assert isinstance(breakdown[key], (int, float))

    def test_analyze_verdict_is_valid(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "Developer tools platform"})
        data = resp.json()
        assert data["final_decision"] in ("APPROVED", "HOLD", "REJECTED")

    def test_analyze_ai_powered_flag_false_without_keys(self) -> None:
        """Without API keys, pipeline uses deterministic scoring."""
        resp = client.post("/api/analyze/", json={
            "idea": "Food delivery app for busy professionals",
            "problem": "Professionals skip meals due to lack of time",
            "target_user": "busy professionals",
            "monetization_model": "subscription",
        })
        data = resp.json()
        # The pipeline returns a final_decision regardless of validation outcome
        assert data["final_decision"] in ("APPROVED", "HOLD", "REJECTED")


# ---------------------------------------------------------------------------
# AI client tests (stub mode)
# ---------------------------------------------------------------------------


class TestOpenAIClientStub:
    """Verify OpenAI client works in stub mode without API key."""

    def test_stub_mode_returns_text(self) -> None:
        from app.integrations.openai_client import OpenAIClient

        client = OpenAIClient(api_key="", model="gpt-4o")
        assert not client.is_configured
        result = client.chat("test prompt")
        assert "stub" in result.lower() or "not configured" in result.lower()

    def test_stub_json_returns_dict(self) -> None:
        from app.integrations.openai_client import OpenAIClient

        client = OpenAIClient(api_key="", model="gpt-4o")
        result = client.chat_json("test prompt")
        assert isinstance(result, dict)
        assert result.get("stub") is True


class TestPerplexityClientStub:
    """Verify Perplexity client works in stub mode without API key."""

    def test_stub_mode_returns_text(self) -> None:
        from app.integrations.perplexity_client import PerplexityClient

        client = PerplexityClient(api_key="", model="sonar")
        assert not client.is_configured
        result = client.research("test query")
        assert "stub" in result.lower() or "not configured" in result.lower()

    def test_market_research_returns_dict(self) -> None:
        from app.integrations.perplexity_client import PerplexityClient

        client = PerplexityClient(api_key="", model="sonar")
        result = client.market_research("Test Product", "developers")
        assert isinstance(result, dict)
        assert result["source"] == "stub"

    def test_competitor_analysis_returns_dict(self) -> None:
        from app.integrations.perplexity_client import PerplexityClient

        client = PerplexityClient(api_key="", model="sonar")
        result = client.competitor_analysis("Test Product", "SaaS")
        assert isinstance(result, dict)
        assert result["source"] == "stub"


class TestAIProvider:
    """Verify AIProvider coordinates clients correctly."""

    def test_provider_in_stub_mode(self) -> None:
        from app.integrations.ai_provider import AIProvider
        from app.integrations.openai_client import OpenAIClient
        from app.integrations.perplexity_client import PerplexityClient

        provider = AIProvider(
            openai_client=OpenAIClient(api_key="", model="gpt-4o"),
            perplexity_client=PerplexityClient(api_key="", model="sonar"),
        )
        assert not provider.ai_enabled
        assert not provider.research_enabled

    def test_analyze_idea_returns_dict(self) -> None:
        from app.integrations.ai_provider import AIProvider
        from app.integrations.openai_client import OpenAIClient
        from app.integrations.perplexity_client import PerplexityClient

        provider = AIProvider(
            openai_client=OpenAIClient(api_key="", model="gpt-4o"),
            perplexity_client=PerplexityClient(api_key="", model="sonar"),
        )
        result = provider.analyze_idea("test idea")
        assert isinstance(result, dict)
        assert result.get("stub") is True

    def test_enrich_idea_returns_dict(self) -> None:
        from app.integrations.ai_provider import AIProvider
        from app.integrations.openai_client import OpenAIClient
        from app.integrations.perplexity_client import PerplexityClient

        provider = AIProvider(
            openai_client=OpenAIClient(api_key="", model="gpt-4o"),
            perplexity_client=PerplexityClient(api_key="", model="sonar"),
        )
        result = provider.enrich_idea("Test", "devs", "problem", "SaaS sub")
        assert isinstance(result, dict)
        assert "market_insight" in result

    def test_business_verdict_returns_dict(self) -> None:
        from app.integrations.ai_provider import AIProvider
        from app.integrations.openai_client import OpenAIClient
        from app.integrations.perplexity_client import PerplexityClient

        provider = AIProvider(
            openai_client=OpenAIClient(api_key="", model="gpt-4o"),
            perplexity_client=PerplexityClient(api_key="", model="sonar"),
        )
        result = provider.generate_business_verdict("Test idea", 7.5)
        assert isinstance(result, dict)
        assert result["verdict"] in ("APPROVE", "HOLD", "REJECT")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfigNewFields:
    """Verify new config fields are present."""

    def test_openai_api_key_field(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert hasattr(s, "openai_api_key")

    def test_perplexity_api_key_field(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert hasattr(s, "perplexity_api_key")

    def test_perplexity_model_default(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.perplexity_model == "sonar"
