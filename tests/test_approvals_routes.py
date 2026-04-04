"""Tests for approval route workflow wiring."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_request_high_impact_action_creates_pending_approval() -> None:
    response = client.post(
        "/approvals/",
        json={
            "action_type": "deploy",
            "payload": {"project_id": "prj-1"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["action_id"]


def test_request_low_impact_action_auto_approves() -> None:
    response = client.post(
        "/approvals/",
        json={
            "action_id": "ext-1",
            "action_type": "create_repo",
            "payload": {"repo": "x"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["action_id"] == "ext-1"


def test_decide_approval_roundtrip() -> None:
    created = client.post(
        "/approvals/",
        json={
            "action_type": "delete_repo",
            "payload": {"repo": "x"},
        },
    )
    assert created.status_code == 200
    action_id = created.json()["action_id"]

    decision = client.post(
        "/approvals/decide",
        json={
            "action_id": action_id,
            "approved": False,
            "reason": "too risky",
        },
    )
    assert decision.status_code == 200
    body = decision.json()
    assert body["action_id"] == action_id
    assert body["status"] == "rejected"
    assert body["reason"] == "too risky"


def test_decide_unknown_approval_returns_404() -> None:
    decision = client.post(
        "/approvals/decide",
        json={
            "action_id": "missing",
            "approved": True,
        },
    )
    assert decision.status_code == 404

