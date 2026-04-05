"""Tests for the command center dashboard root UI."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

TAB_NAMES = [
    "Dashboard Home",
    "Analyze Idea",
    "Portfolio",
    "Factory",
    "Distribution",
    "Revenue",
]


def test_root_returns_200() -> None:
    """GET / must return HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_html() -> None:
    """GET / must return HTML content."""
    response = client.get("/")
    assert "text/html" in response.headers.get("content-type", "")


def test_root_contains_all_tab_names() -> None:
    """GET / must include all six tab names in the HTML."""
    response = client.get("/")
    body = response.text
    for tab in TAB_NAMES:
        assert tab in body, f"Tab '{tab}' not found in root HTML"


def test_root_contains_version() -> None:
    """GET / must embed the current version string."""
    response = client.get("/")
    assert "0.3.0" in response.text


def test_root_has_no_external_deps() -> None:
    """GET / must not reference external CDN URLs."""
    response = client.get("/")
    body = response.text
    forbidden = ["cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
                 "fonts.googleapis.com", "ajax.googleapis.com"]
    for url in forbidden:
        assert url not in body, f"External dependency found: {url}"
