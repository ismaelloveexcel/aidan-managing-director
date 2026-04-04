"""Route tests for feedback ingestion and decision endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.dependencies import get_portfolio_repository
from main import app

client = TestClient(app)


def _project_id() -> str:
    repo = get_portfolio_repository()
    project = repo.create_project(
        name="feedback-route",
        description="feedback route test",
    )
    return project.project_id


def test_feedback_metrics_ingest_endpoint() -> None:
    repo = get_portfolio_repository()
    repo.reset()
    project_id = _project_id()

    response = client.post(
        "/feedback/metrics",
        json={
            "project_id": project_id,
            "visits": 250,
            "signups": 5,
            "revenue": 0,
            "currency": "USD",
            "timestamp": "2026-04-03T12:00:00+00:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["conversion_rate"] == 0.02


def test_feedback_decision_endpoint() -> None:
    repo = get_portfolio_repository()
    repo.reset()
    project_id = _project_id()

    ingest = client.post(
        "/feedback/metrics",
        json={
            "project_id": project_id,
            "visits": 300,
            "signups": 2,
            "revenue": 0,
            "currency": "USD",
            "timestamp": "2026-04-03T13:00:00+00:00",
        },
    )
    assert ingest.status_code == 200

    decision = client.get(f"/feedback/projects/{project_id}/decision")
    assert decision.status_code == 200
    body = decision.json()
    assert body["decision"] == "kill_candidate"
    assert body["suggested_next_state"] == "killed"


def test_feedback_decision_not_found_without_metrics() -> None:
    repo = get_portfolio_repository()
    repo.reset()
    project_id = _project_id()

    decision = client.get(f"/feedback/projects/{project_id}/decision")
    assert decision.status_code == 404

