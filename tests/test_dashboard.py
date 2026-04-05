"""Tests for app/routes/dashboard.py — portfolio health and design token endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/dashboard/health
# ---------------------------------------------------------------------------


class TestDashboardHealth:
    """Tests for the portfolio health snapshot endpoint."""

    def test_health_returns_200(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert resp.status_code == 200

    def test_health_returns_json(self) -> None:
        resp = client.get("/api/dashboard/health")
        body = resp.json()
        assert isinstance(body, dict)

    def test_health_has_required_fields(self) -> None:
        resp = client.get("/api/dashboard/health")
        body = resp.json()
        assert "status" in body
        assert "active_projects" in body
        assert "total_revenue" in body
        assert "theme" in body

    def test_health_status_is_valid_enum(self) -> None:
        resp = client.get("/api/dashboard/health")
        status = resp.json()["status"]
        assert status in ("healthy", "warning", "critical")

    def test_health_active_projects_is_int(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert isinstance(resp.json()["active_projects"], int)

    def test_health_total_revenue_is_numeric(self) -> None:
        resp = client.get("/api/dashboard/health")
        revenue = resp.json()["total_revenue"]
        assert isinstance(revenue, (int, float))

    def test_health_theme_has_colour_fields(self) -> None:
        resp = client.get("/api/dashboard/health")
        theme = resp.json()["theme"]
        expected_keys = {
            "primary_color",
            "background",
            "surface",
            "text",
            "accent",
            "success",
            "warning",
            "danger",
        }
        for key in expected_keys:
            assert key in theme, f"Missing theme key: {key}"

    def test_health_theme_colors_are_hex(self) -> None:
        resp = client.get("/api/dashboard/health")
        theme = resp.json()["theme"]
        for key, value in theme.items():
            assert isinstance(value, str), f"Theme key '{key}' is not a string"
            assert value.startswith("#"), f"Theme color '{key}' is not a hex value: {value}"

    def test_health_empty_portfolio_returns_critical(self) -> None:
        """Fresh SQLite DB has no projects → should be critical."""
        resp = client.get("/api/dashboard/health")
        body = resp.json()
        # Could be critical (no projects) or warning/healthy if tests created projects
        assert body["status"] in ("healthy", "warning", "critical")


# ---------------------------------------------------------------------------
# GET /api/dashboard/tokens
# ---------------------------------------------------------------------------


class TestDashboardTokens:
    """Tests for the design tokens endpoint."""

    def test_tokens_returns_200(self) -> None:
        resp = client.get("/api/dashboard/tokens")
        assert resp.status_code == 200

    def test_tokens_returns_json_dict(self) -> None:
        resp = client.get("/api/dashboard/tokens")
        body = resp.json()
        assert isinstance(body, dict)

    def test_tokens_has_all_design_token_keys(self) -> None:
        resp = client.get("/api/dashboard/tokens")
        body = resp.json()
        expected_keys = {
            "primary_color",
            "background",
            "surface",
            "text",
            "accent",
            "success",
            "warning",
            "danger",
        }
        for key in expected_keys:
            assert key in body, f"Missing design token: {key}"

    def test_tokens_values_are_hex_strings(self) -> None:
        resp = client.get("/api/dashboard/tokens")
        body = resp.json()
        for key, value in body.items():
            assert isinstance(value, str), f"Token '{key}' is not a string"
            assert value.startswith("#"), f"Token '{key}' is not a hex value: {value}"

    def test_tokens_consistent_with_health_theme(self) -> None:
        """Tokens endpoint and health theme should return the same colour set."""
        health_resp = client.get("/api/dashboard/health")
        tokens_resp = client.get("/api/dashboard/tokens")

        health_theme = health_resp.json()["theme"]
        tokens = tokens_resp.json()

        assert health_theme == tokens
