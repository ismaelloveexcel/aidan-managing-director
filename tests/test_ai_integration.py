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
        assert "idea-input" in resp.text
        assert "submit-btn" in resp.text

    def test_root_contains_analyze_endpoint(self) -> None:
        resp = client.get("/")
        assert "/api/analyze/" in resp.text

    def test_root_does_not_use_innerhtml_for_verdict(self) -> None:
        """Verify the XSS fix: verdict rendering uses textContent, not innerHTML."""
        resp = client.get("/")
        assert "verdictSpan.textContent=v" in resp.text


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
        assert data["success"] is True
        assert "analysis" in data
        analysis = data["analysis"]
        assert "title" in analysis
        assert "target_user" in analysis
        assert "monetization_method" in analysis
        assert "pricing_suggestion" in analysis
        assert "distribution_plan" in analysis
        assert "overall_score" in analysis
        assert "verdict" in analysis

    def test_analyze_has_monetization_fields(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "AI chatbot for e-commerce"})
        analysis = resp.json()["analysis"]
        assert analysis["monetization_method"]
        assert analysis["pricing_suggestion"]
        assert analysis["distribution_plan"]
        assert analysis["first_10_users"]

    def test_analyze_includes_pipeline_result(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "Marketplace for tutors"})
        data = resp.json()
        assert data["pipeline_result"] is not None
        assert "score" in data["pipeline_result"]
        assert "strategy" in data["pipeline_result"]

    def test_analyze_rejects_empty_input(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": ""})
        assert resp.status_code == 422

    def test_analyze_rejects_missing_field(self) -> None:
        resp = client.post("/api/analyze/", json={})
        assert resp.status_code == 422

    def test_analyze_scores_are_numeric(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "SaaS dashboard for HR teams"})
        analysis = resp.json()["analysis"]
        assert isinstance(analysis["overall_score"], (int, float))
        assert isinstance(analysis["feasibility_score"], (int, float))
        assert isinstance(analysis["profitability_score"], (int, float))
        assert isinstance(analysis["speed_score"], (int, float))
        assert isinstance(analysis["competition_score"], (int, float))

    def test_analyze_verdict_is_valid(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": "Developer tools platform"})
        analysis = resp.json()["analysis"]
        assert analysis["verdict"] in ("APPROVE", "HOLD", "REJECT", "approve", "hold", "reject")

    def test_analyze_ai_powered_flag_false_without_keys(self) -> None:
        """Without API keys, ai_powered should be False (no real AI call succeeded)."""
        resp = client.post("/api/analyze/", json={"idea": "Food delivery app"})
        analysis = resp.json()["analysis"]
        assert analysis["ai_powered"] is False


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
