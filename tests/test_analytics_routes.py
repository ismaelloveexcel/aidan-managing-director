"""Tests for the analytics route."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_record_analytics_event() -> None:
    response = client.post("/analytics/events", json={
        "project_id": "prj-test",
        "event_type": "page_view",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["project_id"] == "prj-test"


def test_invalid_event_type() -> None:
    response = client.post("/analytics/events", json={
        "project_id": "prj-test",
        "event_type": "invalid_type",
    })
    assert response.status_code == 400


def test_analytics_summary_empty() -> None:
    response = client.get("/analytics/projects/nonexistent/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["events_recorded"] == 0


def test_analytics_summary_with_events() -> None:
    # Record some events first
    for _ in range(3):
        client.post("/analytics/events", json={
            "project_id": "prj-summary",
            "event_type": "page_view",
        })
    client.post("/analytics/events", json={
        "project_id": "prj-summary",
        "event_type": "signup",
    })
    client.post("/analytics/events", json={
        "project_id": "prj-summary",
        "event_type": "purchase",
        "value": 29.99,
    })

    response = client.get("/analytics/projects/prj-summary/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_page_views"] >= 3
    assert data["total_signups"] >= 1
    assert data["total_purchases"] >= 1
    assert data["total_revenue"] >= 29.99
