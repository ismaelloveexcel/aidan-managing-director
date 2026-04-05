"""Tests for the root command center dashboard UI."""

from fastapi.testclient import TestClient

from main import app, _VERSION

client = TestClient(app)


def test_root_returns_200() -> None:
    """GET / should return HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_html() -> None:
    """GET / should return an HTML document."""
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_root_contains_version() -> None:
    """GET / should contain the current version string."""
    response = client.get("/")
    assert _VERSION in response.text


def test_root_contains_tab_labels() -> None:
    """GET / should contain all six tab labels."""
    response = client.get("/")
    html = response.text
    for label in ["Dashboard", "Analyze Idea", "Portfolio", "Factory", "Distribution", "Revenue"]:
        assert label in html, f"Tab label '{label}' not found in root HTML"


def test_root_contains_api_endpoints() -> None:
    """GET / should reference the key API endpoints used by the dashboard."""
    response = client.get("/")
    html = response.text
    for endpoint in ["/api/analyze/", "/portfolio/projects", "/factory/runs",
                     "/api/distribution/share-messages", "/revenue/projects"]:
        assert endpoint in html, f"API endpoint '{endpoint}' not found in root HTML"
