"""Tests for registry-backed project, idea, and command routes."""

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_registry_client
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Clear shared registry stub storage between tests."""
    get_registry_client().reset()


class TestProjectRoutes:
    """Project portfolio endpoints."""

    def test_create_project(self) -> None:
        resp = client.post(
            "/projects/",
            json={"name": "test-proj", "description": "A test project"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "test-proj"
        assert body["status"] == "active"
        assert "project_id" in body
        assert "created_at" in body

    def test_create_project_with_repo_url(self) -> None:
        resp = client.post(
            "/projects/",
            json={
                "name": "repo-proj",
                "description": "Has repo",
                "repository_url": "https://github.com/org/repo",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["metadata"]["repository_url"] == "https://github.com/org/repo"

    def test_list_projects_empty(self) -> None:
        resp = client.get("/projects/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_project_not_found(self) -> None:
        resp = client.get("/projects/nonexistent-id")
        assert resp.status_code == 404

    def test_create_then_get(self) -> None:
        create_resp = client.post(
            "/projects/",
            json={"name": "findable", "description": "Can be found"},
        )
        project_id = create_resp.json()["project_id"]
        get_resp = client.get(f"/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["project_id"] == project_id

    def test_update_project_status(self) -> None:
        create_resp = client.post(
            "/projects/",
            json={"name": "status-test", "description": "For status update"},
        )
        project_id = create_resp.json()["project_id"]
        patch_resp = client.patch(
            f"/projects/{project_id}/status",
            json={"status": "paused"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "paused"

    def test_update_status_not_found(self) -> None:
        resp = client.patch(
            "/projects/does-not-exist/status",
            json={"status": "archived"},
        )
        assert resp.status_code == 404

    def test_update_status_invalid_value(self) -> None:
        create_resp = client.post(
            "/projects/",
            json={"name": "val-test", "description": "For validation"},
        )
        project_id = create_resp.json()["project_id"]
        resp = client.patch(
            f"/projects/{project_id}/status",
            json={"status": "banana"},
        )
        assert resp.status_code == 422  # Pydantic validation error


class TestIdeaPersistence:
    """Ideas routes persist generated ideas via the registry."""

    def test_generate_still_returns_idea(self) -> None:
        resp = client.post("/ideas/generate", json={"prompt": "healthcare tools"})
        assert resp.status_code == 200
        body = resp.json()
        assert "idea_id" in body
        assert "title" in body

    def test_brainstorm_still_returns_ideas(self) -> None:
        resp = client.post(
            "/ideas/brainstorm",
            json={"prompt": "marketing tools", "count": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_evaluate_unchanged(self) -> None:
        gen = client.post("/ideas/generate", json={"prompt": "fintech"})
        idea = gen.json()
        resp = client.post("/ideas/evaluate", json={"idea": idea})
        assert resp.status_code == 200
        body = resp.json()
        assert "total_score" in body
        assert "breakdown" in body
        assert "decision" in body

    def test_critique_unchanged(self) -> None:
        gen = client.post("/ideas/generate", json={"prompt": "fintech"})
        idea = gen.json()
        resp = client.post("/ideas/critique", json={"idea": idea})
        assert resp.status_code == 200
        assert "verdict" in resp.json()


class TestCommandRoutes:
    """Command dispatch endpoints."""

    def test_dispatch_command(self) -> None:
        resp = client.post(
            "/commands/dispatch",
            json={"command_type": "create_repo", "parameters": {"name": "repo"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["record_id"].startswith("cmd-")
        assert body["status"] == "pending"
        assert body["command_type"] == "create_repo"

    def test_dispatch_with_project_id(self) -> None:
        resp = client.post(
            "/commands/dispatch",
            json={
                "command_type": "deploy",
                "parameters": {},
                "project_id": "proj-xyz",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "proj-xyz"

    def test_get_command_status_not_found(self) -> None:
        resp = client.get("/commands/some-id")
        assert resp.status_code == 404

    def test_get_command_status_for_dispatched_command(self) -> None:
        dispatch = client.post(
            "/commands/dispatch",
            json={"command_type": "deploy", "parameters": {"env": "prod"}},
        )
        assert dispatch.status_code == 200
        command_id = dispatch.json()["record_id"]

        resp = client.get(f"/commands/{command_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["command_id"] == command_id
        assert body["status"] == "pending"
