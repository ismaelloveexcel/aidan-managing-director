"""API tests for factory validation and run endpoints."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_factory_run_store, get_portfolio_repository
from main import app

client = TestClient(app)


def _ensure_project(project_id: str) -> None:
    """Ensure a project row exists so FK constraints on factory_runs pass."""
    repo = get_portfolio_repository()
    if repo.get_project(project_id) is None:
        repo.create_project(
            name=project_id,
            description="Test project for factory route tests",
            project_id=project_id,
        )


def _payload() -> dict:
    return {
        "project_id": "PRJ-API-1",
        "idea_id": "IDEA-API-1",
        "hypothesis": "A focused landing page can capture demand quickly.",
        "target_user": "indie founders",
        "problem": "Idea validation is too slow and manual.",
        "solution": "Automatically generate and deploy single-purpose MVP pages.",
        "mvp_scope": ["Landing page", "CTA endpoint"],
        "acceptance_criteria": ["Page loads", "CTA submits successfully"],
        "landing_page_requirements": [
            "Primary CTA: Get early access",
            "Clear value proposition above the fold",
        ],
        "cta": "Get early access",
        "pricing_hint": "Free waitlist",
        "deployment_target": "vercel",
        "command_bundle": {"entrypoint": "factory.run"},
        "feature_flags": {"dry_run": True, "live_factory": False},
    }


def test_validate_brief_endpoint() -> None:
    get_factory_run_store().reset()
    response = client.post("/factory/briefs/validate", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["brief_hash"] is not None
    assert body["idempotency_key"].startswith("PRJ-API-1:")


def test_create_run_endpoint() -> None:
    get_factory_run_store().reset()
    _ensure_project("PRJ-API-1")
    response = client.post(
        "/factory/runs",
        json={"build_brief": _payload(), "dry_run": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["repo_url"].startswith("dry-run://github/")
    assert body["deploy_url"].startswith("dry-run://vercel/")


def test_get_missing_run_endpoint() -> None:
    get_factory_run_store().reset()
    response = client.get("/factory/runs/non-existent-run")
    assert response.status_code == 404


def test_tracking_endpoint_returns_workflow_metadata() -> None:
    get_factory_run_store().reset()
    _ensure_project("PRJ-API-1")
    created = client.post(
        "/factory/runs",
        json={"build_brief": _payload(), "dry_run": True},
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    tracking = client.get(f"/factory/runs/{run_id}/tracking")
    assert tracking.status_code == 200
    body = tracking.json()
    assert body["run_id"] == run_id
    assert isinstance(body["workflow_dispatched"], bool)
    assert body["workflow_run_id"].startswith("ghrun-")
    assert body["repo_url"].startswith("dry-run://github/")
    assert body["deployment_url"].startswith("dry-run://vercel/")


def test_execute_idea_flow_triggers_approved_build() -> None:
    get_factory_run_store().reset()
    get_portfolio_repository().reset()
    response = client.post(
        "/factory/ideas/execute",
        json={
            "message": (
                "Create a compliance automation product for small clinics. "
                "They lose revenue from manual repetitive work and need faster workflow automation. "
                "Pricing: subscription $79/month."
            ),
            "project_id": "PRJ-E2E-CV",
            "dry_run": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approved_for_build"] is True
    assert body["decision"] == "APPROVE"
    assert body["project_id"] == "PRJ-E2E-CV"
    assert body["status"] == "succeeded"
    assert isinstance(body["workflow_dispatched"], bool)
    assert body["repo_url"].startswith("dry-run://github/")
    assert body["deployment_url"].startswith("dry-run://vercel/")

