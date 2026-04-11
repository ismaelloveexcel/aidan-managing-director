"""Tests for the dashboard routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app, raise_server_exceptions=True)


class TestDashboardHealth:
    """Tests for GET /api/dashboard/health."""

    def test_returns_200(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert resp.status_code == 200

    def test_response_has_required_fields(self) -> None:
        resp = client.get("/api/dashboard/health")
        data = resp.json()
        assert "total_projects" in data
        assert "approved_count" in data
        assert "revenue_total" in data
        assert "blocked_count" in data
        assert "health_status" in data
        assert "summary" in data

    def test_health_status_is_valid_enum(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert resp.json()["health_status"] in {"GREEN", "AMBER", "RED"}

    def test_counts_are_non_negative(self) -> None:
        resp = client.get("/api/dashboard/health")
        data = resp.json()
        assert data["total_projects"] >= 0
        assert data["approved_count"] >= 0
        assert data["blocked_count"] >= 0

    def test_revenue_is_numeric(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert isinstance(resp.json()["revenue_total"], (int, float))

    def test_summary_is_string(self) -> None:
        resp = client.get("/api/dashboard/health")
        assert isinstance(resp.json()["summary"], str)
        assert len(resp.json()["summary"]) > 0


class TestDashboardTokens:
    """Tests for GET /api/dashboard/tokens."""

    def test_returns_200(self) -> None:
        resp = client.get("/api/dashboard/tokens")
        assert resp.status_code == 200

    def test_required_colour_fields_present(self) -> None:
        data = client.get("/api/dashboard/tokens").json()
        for field in ("primary", "surface", "text", "success", "warning", "danger", "border"):
            assert field in data
            assert data[field].startswith("#")

    def test_radius_field_present(self) -> None:
        data = client.get("/api/dashboard/tokens").json()
        assert "radius" in data
        assert "px" in data["radius"]

    def test_font_family_present(self) -> None:
        data = client.get("/api/dashboard/tokens").json()
        assert "font_family" in data
        assert len(data["font_family"]) > 0

    def test_font_sizes_dict_present(self) -> None:
        data = client.get("/api/dashboard/tokens").json()
        assert "font_sizes" in data
        assert isinstance(data["font_sizes"], dict)
        assert "base" in data["font_sizes"]


class TestDashboardHealthLogic:
    """Unit tests for the _compute_health helper."""

    def test_green_when_revenue_positive(self) -> None:
        from app.routes.dashboard import _compute_health

        status, _ = _compute_health(total=5, approved=1, revenue_total=500.0, blocked=0)
        assert status == "GREEN"

    def test_green_when_three_or_more_approved(self) -> None:
        from app.routes.dashboard import _compute_health

        status, _ = _compute_health(total=5, approved=3, revenue_total=0.0, blocked=0)
        assert status == "GREEN"

    def test_amber_when_projects_no_revenue(self) -> None:
        from app.routes.dashboard import _compute_health

        status, _ = _compute_health(total=2, approved=1, revenue_total=0.0, blocked=0)
        assert status == "AMBER"

    def test_red_when_no_projects(self) -> None:
        from app.routes.dashboard import _compute_health

        status, _ = _compute_health(total=0, approved=0, revenue_total=0.0, blocked=0)
        assert status == "RED"

    def test_red_when_blocked_projects(self) -> None:
        from app.routes.dashboard import _compute_health

        status, _ = _compute_health(total=3, approved=1, revenue_total=0.0, blocked=1)
        assert status == "RED"

    def test_summary_is_non_empty_string(self) -> None:
        from app.routes.dashboard import _compute_health

        _, summary = _compute_health(total=1, approved=0, revenue_total=0.0, blocked=0)
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestApprovedStates:
    """Verify _APPROVED_STATES includes post-build lifecycle states."""

    def test_launched_and_monitoring_in_approved_states(self) -> None:
        from app.portfolio.models import LifecycleState
        from app.routes.dashboard import _APPROVED_STATES

        assert LifecycleState.LAUNCHED in _APPROVED_STATES
        assert LifecycleState.MONITORING in _APPROVED_STATES
        assert LifecycleState.SCALED in _APPROVED_STATES

    def test_killed_not_in_approved_states(self) -> None:
        from app.portfolio.models import LifecycleState
        from app.routes.dashboard import _APPROVED_STATES

        assert LifecycleState.KILLED not in _APPROVED_STATES
