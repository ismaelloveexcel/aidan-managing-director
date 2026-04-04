"""Focused integration tests for decision-to-factory bridge."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_command_center_service, get_portfolio_repository
from main import app

client = TestClient(app)


def test_execute_idea_build_dry_run_and_tracking() -> None:
    repo = get_portfolio_repository()
    repo.reset()

    response = client.post(
        "/factory/ideas/execute",
        json={
            "message": "Idea: AI tool that scores CVs and matches jobs",
            "project_id": "PRJ-E2E-CV-1",
            "dry_run": True,
            "force_approve_build": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approved_for_build"] is True
    assert body["decision"] == "APPROVE_BUILD"
    assert body["status"] == "succeeded"
    assert body["repo_url"].startswith("dry-run://github/")
    assert body["deployment_url"].startswith("dry-run://vercel/")
    assert body["workflow_dispatched"] is True
    assert body["run_id"]

    tracking = client.get(f"/factory/runs/{body['run_id']}/tracking")
    assert tracking.status_code == 200
    tracking_body = tracking.json()
    assert tracking_body["workflow_dispatched"] is True
    assert tracking_body["status"] == "succeeded"
    assert tracking_body["repo_url"] == body["repo_url"]
    assert tracking_body["deployment_url"] == body["deployment_url"]


def test_command_center_state_reflects_latest_build_links() -> None:
    # Execute a run first.
    execute = client.post(
        "/factory/ideas/execute",
        json={
            "message": "Idea: AI tool that scores CVs and matches jobs",
            "project_id": "PRJ-E2E-CV-2",
            "dry_run": True,
            "force_approve_build": True,
        },
    )
    assert execute.status_code == 200

    state = client.get("/control/state")
    assert state.status_code == 200
    body = state.json()
    assert "latest_build" in body
    latest_build = body["latest_build"]
    assert latest_build is not None
    assert latest_build["project_id"]
    assert latest_build["status"] in {"succeeded", "failed", "running", "pending"}
    assert latest_build["repo_url"] is not None
    assert latest_build["deployment_url"] is not None

    # Ensure command center service returns the same shape directly.
    service_state = get_command_center_service().overview()
    assert service_state.latest_build is not None
    assert service_state.latest_build.project_name
