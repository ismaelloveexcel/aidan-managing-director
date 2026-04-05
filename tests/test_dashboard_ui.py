"""Tests for the root command-center dashboard UI (GET /)."""

from fastapi.testclient import TestClient

from main import app, _VERSION

client = TestClient(app)


def _get_html() -> str:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    return response.text


def test_root_returns_200() -> None:
    response = client.get("/")
    assert response.status_code == 200


def test_root_content_type_is_html() -> None:
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_version_injected() -> None:
    html = _get_html()
    assert _VERSION in html


def test_tab_dashboard_present() -> None:
    html = _get_html()
    assert "tab-dashboard" in html
    assert "Dashboard" in html


def test_tab_analyze_present() -> None:
    html = _get_html()
    assert "tab-analyze" in html
    assert "Analyze" in html


def test_tab_portfolio_present() -> None:
    html = _get_html()
    assert "tab-portfolio" in html
    assert "Portfolio" in html


def test_tab_factory_present() -> None:
    html = _get_html()
    assert "tab-factory" in html
    assert "Factory" in html


def test_tab_distribution_present() -> None:
    html = _get_html()
    assert "tab-distribution" in html
    assert "Distribution" in html


def test_tab_revenue_present() -> None:
    html = _get_html()
    assert "tab-revenue" in html
    assert "Revenue" in html


def test_analyze_form_fields_present() -> None:
    html = _get_html()
    for field_id in ("idea", "problem", "target_user", "monetization_model",
                     "competition_level", "difficulty", "time_to_revenue",
                     "differentiation"):
        assert f'id="{field_id}"' in html, f"Missing form field: {field_id}"


def test_approve_and_build_button_present() -> None:
    html = _get_html()
    assert "approveBuildBtn" in html
    assert "Approve" in html


def test_portfolio_table_structure_present() -> None:
    html = _get_html()
    assert "portfolioBody" in html
    assert "portfolioTable" in html


def test_factory_runs_table_present() -> None:
    html = _get_html()
    assert "factoryBody" in html
    assert "factoryTable" in html


def test_distribution_form_fields_present() -> None:
    html = _get_html()
    for field_id in ("distTitle", "distUrl", "distDesc", "distUser", "distCta"):
        assert f'id="{field_id}"' in html, f"Missing distribution field: {field_id}"


def test_revenue_section_present() -> None:
    html = _get_html()
    assert "revProjectId" in html
    assert "bizProjectId" in html


def test_stats_cards_present() -> None:
    html = _get_html()
    for stat_id in ("st-total", "st-approved", "st-building", "st-launched", "st-killed"):
        assert f'id="{stat_id}"' in html, f"Missing stat card: {stat_id}"


def test_api_key_input_present() -> None:
    html = _get_html()
    assert "apiKeyInput" in html
    assert "saveApiKey" in html


def test_health_dot_present() -> None:
    html = _get_html()
    assert "healthDot" in html


def test_toast_container_present() -> None:
    html = _get_html()
    assert "toastWrap" in html


def test_modal_present() -> None:
    html = _get_html()
    assert "modalOverlay" in html


def test_no_external_dependencies() -> None:
    """Ensure the dashboard has no CDN or external script/link tags."""
    html = _get_html()
    assert "cdn.jsdelivr.net" not in html
    assert "cdnjs.cloudflare.com" not in html
    assert "unpkg.com" not in html
    assert "tailwindcss.com" not in html


def test_factory_list_runs_endpoint() -> None:
    """GET /factory/runs should return a list (may be empty)."""
    response = client.get("/factory/runs", headers={"X-API-Key": "test"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_factory_verify_deployment_invalid_url() -> None:
    """POST /factory/verify-deployment with an invalid URL is rejected (SSRF protection)."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj", "deploy_url": "not-a-url"},
        headers={"X-API-Key": "test"},
    )
    # non-public URLs are rejected at the route level
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.json()["status"] == "failed"


def test_factory_verify_deployment_missing_url() -> None:
    """POST /factory/verify-deployment with no URL returns FAILED status."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj"},
        headers={"X-API-Key": "test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"


def test_factory_verify_deployment_blocks_localhost() -> None:
    """POST /factory/verify-deployment should reject localhost to prevent SSRF."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj", "deploy_url": "http://localhost/health"},
        headers={"X-API-Key": "test"},
    )
    assert response.status_code == 422


def test_factory_verify_deployment_blocks_private_ip() -> None:
    """POST /factory/verify-deployment should reject private IP ranges (SSRF protection)."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj", "deploy_url": "http://192.168.1.1/health"},
        headers={"X-API-Key": "test"},
    )
    assert response.status_code == 422
