"""Tests for the premium dashboard routes and summary endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app, raise_server_exceptions=True)


class TestDashboardSummary:
    """Tests for GET /api/dashboard/summary."""

    def test_returns_200(self) -> None:
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200

    def test_has_required_fields(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        assert "projects" in data
        assert "stats" in data
        assert "health" in data
        assert "recent_builds" in data
        assert "issues" in data

    def test_projects_is_list(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        assert isinstance(data["projects"], list)

    def test_stats_has_expected_keys(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        stats = data["stats"]
        assert "total_projects" in stats
        assert "approved_count" in stats
        assert "revenue_total" in stats
        assert "venture_count" in stats
        assert "personal_count" in stats
        assert "build_count" in stats

    def test_health_has_status(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        assert data["health"]["health_status"] in {"GREEN", "AMBER", "RED"}

    def test_issues_is_list(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        assert isinstance(data["issues"], list)

    def test_recent_builds_is_list(self) -> None:
        data = client.get("/api/dashboard/summary").json()
        assert isinstance(data["recent_builds"], list)


class TestProjectTypeUpdate:
    """Tests for PATCH /api/dashboard/projects/{id}/type."""

    def test_nonexistent_project_returns_404(self) -> None:
        resp = client.patch(
            "/api/dashboard/projects/nonexistent-id/type",
            json={"project_type": "personal"},
        )
        assert resp.status_code == 404

    def test_invalid_type_returns_422(self) -> None:
        resp = client.patch(
            "/api/dashboard/projects/some-id/type",
            json={"project_type": "invalid"},
        )
        assert resp.status_code == 422


class TestPremiumDashboardRoute:
    """Tests for GET /dashboard (premium dashboard HTML)."""

    def test_returns_200(self) -> None:
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_returns_html(self) -> None:
        resp = client.get("/dashboard")
        assert "text/html" in resp.headers["content-type"]

    def test_contains_dashboard_markup(self) -> None:
        resp = client.get("/dashboard")
        assert "AI-DAN" in resp.text
        assert "Founder Dashboard" in resp.text
        assert "Command Center" in resp.text

    def test_loads_static_assets(self) -> None:
        resp = client.get("/dashboard")
        assert "/static/css/dashboard.css" in resp.text
        assert "/static/js/dashboard.js" in resp.text


class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_accessible(self) -> None:
        resp = client.get("/static/css/dashboard.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_js_accessible(self) -> None:
        resp = client.get("/static/js/dashboard.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]


class TestLegacyRootRoute:
    """Ensure the legacy root UI still works."""

    def test_root_returns_200(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_returns_html(self) -> None:
        resp = client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_root_contains_legacy_ui(self) -> None:
        resp = client.get("/")
        assert "AI-DAN" in resp.text


class TestProjectSummaryModel:
    """Tests for ProjectSummary helper."""

    def test_project_to_summary_default_type(self) -> None:
        from app.routes.dashboard import _project_to_summary
        from app.portfolio.models import LifecycleState

        class FakeProject:
            project_id = "test-1"
            name = "Test Project"
            description = "A test"
            status = LifecycleState.IDEA
            metadata = {}
            created_at = "2024-01-01T00:00:00Z"
            updated_at = "2024-01-01T00:00:00Z"

        summary = _project_to_summary(FakeProject())
        assert summary.project_type == "venture"
        assert summary.revenue == 0.0

    def test_project_to_summary_personal_type(self) -> None:
        from app.routes.dashboard import _project_to_summary
        from app.portfolio.models import LifecycleState

        class FakeProject:
            project_id = "test-2"
            name = "My Tool"
            description = "Personal utility"
            status = LifecycleState.BUILDING
            metadata = {"project_type": "personal", "revenue": 100}
            created_at = "2024-01-01T00:00:00Z"
            updated_at = "2024-01-01T00:00:00Z"

        summary = _project_to_summary(FakeProject())
        assert summary.project_type == "personal"
        assert summary.revenue == 100.0


class TestDetectIssues:
    """Tests for _detect_issues helper."""

    def test_empty_portfolio_returns_info_issue(self) -> None:
        from app.routes.dashboard import _detect_issues

        issues = _detect_issues([])
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert "empty" in issues[0].description.lower()

    def test_killed_project_returns_warning(self) -> None:
        from app.routes.dashboard import _detect_issues
        from app.portfolio.models import LifecycleState

        class FakeKilled:
            project_id = "k1"
            name = "Dead Project"
            status = LifecycleState.KILLED

        issues = _detect_issues([FakeKilled()])
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) >= 1
