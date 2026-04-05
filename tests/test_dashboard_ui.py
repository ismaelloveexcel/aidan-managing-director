"""Tests for the full command-centre dashboard served at GET /."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestDashboardTabs:
    """Verify that GET / includes all six tab labels."""

    def test_dashboard_returns_200(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_dashboard_tab_present(self) -> None:
        resp = client.get("/")
        assert "Dashboard" in resp.text

    def test_analyze_tab_present(self) -> None:
        resp = client.get("/")
        assert "Analyze Idea" in resp.text

    def test_portfolio_tab_present(self) -> None:
        resp = client.get("/")
        assert "Portfolio" in resp.text

    def test_factory_tab_present(self) -> None:
        resp = client.get("/")
        assert "Factory" in resp.text

    def test_distribution_tab_present(self) -> None:
        resp = client.get("/")
        assert "Distribution" in resp.text

    def test_revenue_tab_present(self) -> None:
        resp = client.get("/")
        assert "Revenue" in resp.text

    def test_version_bumped_to_030(self) -> None:
        resp = client.get("/")
        assert "0.3.0" in resp.text

    def test_analyze_form_preserved(self) -> None:
        """Existing analyze form fields must still be present."""
        resp = client.get("/")
        for field_id in ["idea", "analyzeBtn", "problem", "target_user",
                         "monetization_model", "competition_level",
                         "difficulty", "time_to_revenue", "differentiation"]:
            assert f'id="{field_id}"' in resp.text, f"Missing id={field_id}"

    def test_loading_and_error_states_preserved(self) -> None:
        resp = client.get("/")
        assert 'id="loading"' in resp.text
        assert "spinner" in resp.text
        assert 'id="errorBox"' in resp.text

    def test_api_analyze_endpoint_referenced(self) -> None:
        resp = client.get("/")
        assert "/api/analyze/" in resp.text

    def test_xss_safe_escape_html(self) -> None:
        resp = client.get("/")
        assert "escapeHtml" in resp.text

    def test_toast_container_present(self) -> None:
        resp = client.get("/")
        assert "toastContainer" in resp.text

    def test_tab_switching_function_present(self) -> None:
        resp = client.get("/")
        assert "showTab" in resp.text

    def test_auto_refresh_interval_present(self) -> None:
        resp = client.get("/")
        assert "setInterval" in resp.text

    def test_stat_cards_present(self) -> None:
        resp = client.get("/")
        for stat_id in ["statTotal", "statApproved", "statBuilding", "statLaunched"]:
            assert stat_id in resp.text, f"Missing stat card {stat_id}"

    def test_health_indicator_present(self) -> None:
        resp = client.get("/")
        assert "healthIndicator" in resp.text

    def test_portfolio_table_present(self) -> None:
        resp = client.get("/")
        assert "portfolioTable" in resp.text

    def test_factory_table_present(self) -> None:
        resp = client.get("/")
        assert "factoryTable" in resp.text

    def test_distribution_form_present(self) -> None:
        resp = client.get("/")
        assert "generateMessages" in resp.text

    def test_revenue_section_present(self) -> None:
        resp = client.get("/")
        assert "revProjectId" in resp.text


class TestFactoryRunsEndpoint:
    """Verify the new GET /factory/runs endpoint works."""

    def test_list_runs_returns_200(self) -> None:
        from app.core.dependencies import get_factory_run_store
        get_factory_run_store().reset()
        resp = client.get("/factory/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_runs_includes_created_run(self) -> None:
        from app.core.dependencies import get_factory_run_store
        get_factory_run_store().reset()
        payload = {
            "build_brief": {
                "project_id": "PRJ-LIST-1",
                "idea_id": "IDEA-LIST-1",
                "hypothesis": "A focused landing page can capture demand quickly.",
                "target_user": "indie founders",
                "problem": "Idea validation is too slow and manual.",
                "solution": "Automatically generate and deploy single-purpose MVP pages.",
                "mvp_scope": ["Landing page", "CTA endpoint"],
                "acceptance_criteria": ["Page loads"],
                "landing_page_requirements": ["Primary CTA: Get early access"],
                "cta": "Get early access",
                "pricing_hint": "Free waitlist",
                "deployment_target": "vercel",
                "command_bundle": {"entrypoint": "factory.run"},
                "feature_flags": {"dry_run": True, "live_factory": False},
            },
            "dry_run": True,
        }
        client.post("/factory/runs", json=payload)
        resp = client.get("/factory/runs")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) >= 1
        assert any(r["project_id"] == "PRJ-LIST-1" for r in runs)


class TestVerifyDeploymentEndpoint:
    """Verify the new POST /factory/verify-deployment endpoint works."""

    def test_verify_deployment_returns_200(self) -> None:
        resp = client.post(
            "/factory/verify-deployment",
            json={"project_id": "prj-test", "deploy_url": ""},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == "prj-test"
        assert "status" in body

    def test_verify_deployment_with_url(self) -> None:
        resp = client.post(
            "/factory/verify-deployment",
            json={"project_id": "prj-abc", "deploy_url": "https://example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == "prj-abc"
