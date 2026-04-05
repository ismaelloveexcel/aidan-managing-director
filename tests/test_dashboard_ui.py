"""Basic tests for the root command center dashboard UI."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_factory_run_store
from main import app

client = TestClient(app)


def test_root_returns_200() -> None:
    """GET / should return HTTP 200 with HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_root_contains_dashboard_tabs() -> None:
    """GET / should return the 6-tab command center dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "AI-DAN" in body
    # Check that all 6 tabs are present
    assert "Dashboard" in body
    assert "Analyze" in body
    assert "Portfolio" in body
    assert "Factory" in body
    assert "Distribution" in body
    assert "Revenue" in body


def test_root_contains_version() -> None:
    """GET / should include the current version string."""
    response = client.get("/")
    assert response.status_code == 200
    assert "0.3.0" in response.text


def test_factory_list_runs_empty() -> None:
    """GET /factory/runs should return an empty list when no runs exist."""
    get_factory_run_store().reset()
    response = client.get("/factory/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_factory_verify_deployment_missing_url() -> None:
    """POST /factory/verify-deployment with no URL should return FAILED status."""
    response = client.post(
        "/factory/verify-deployment",
        json={"project_id": "test-proj", "deploy_url": "", "repo_url": ""},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "test-proj"
    assert body["status"] == "failed"
