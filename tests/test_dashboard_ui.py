"""Basic smoke tests for the root command center dashboard."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

_EXPECTED_TABS = [
    "Dashboard",
    "Analyze Idea",
    "Portfolio",
    "Factory",
    "Distribution",
    "Revenue",
]


def test_root_returns_200() -> None:
    response = client.get("/")
    assert response.status_code == 200


def test_root_content_type_is_html() -> None:
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_root_contains_all_tab_names() -> None:
    response = client.get("/")
    body = response.text
    for tab in _EXPECTED_TABS:
        assert tab in body, f"Expected tab '{tab}' not found in dashboard HTML"


def test_root_contains_version() -> None:
    response = client.get("/")
    assert "0.3.0" in response.text


def test_root_contains_command_center_title() -> None:
    response = client.get("/")
    assert "Command Center" in response.text


def test_factory_list_runs_endpoint() -> None:
    """GET /factory/runs should return a list."""
    response = client.get("/factory/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_factory_verify_deployment_endpoint() -> None:
    """POST /factory/verify-deployment should return a verification result."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj", "deploy_url": "https://example.com", "repo_url": "https://github.com/test/repo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "test-prj"
    assert "status" in body
    assert "checks_performed" in body


def test_factory_verify_deployment_missing_url() -> None:
    """POST /factory/verify-deployment with no URL returns failed status."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-prj", "deploy_url": "", "repo_url": ""},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
