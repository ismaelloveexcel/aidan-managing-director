"""Tests for the unified analyze endpoint and root UI."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestRootUI:
    """Tests for the root UI endpoint."""

    def test_root_returns_html(self) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "AI-DAN Managing Director" in resp.text

    def test_root_has_form(self) -> None:
        resp = client.get("/")
        assert 'id="idea"' in resp.text
        assert 'id="analyzeBtn"' in resp.text

    def test_root_has_fields(self) -> None:
        resp = client.get("/")
        for field in ["problem", "target_user", "monetization_model",
                      "competition_level", "difficulty", "time_to_revenue",
                      "differentiation"]:
            assert f'id="{field}"' in resp.text

    def test_root_has_loading_state(self) -> None:
        resp = client.get("/")
        assert 'id="analyzeLoading"' in resp.text
        assert "spinner" in resp.text

    def test_root_has_error_state(self) -> None:
        resp = client.get("/")
        assert 'id="analyzeError"' in resp.text


class TestAnalyzeEndpoint:
    """Tests for POST /api/analyze/."""

    def test_analyze_valid_idea(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "SaaS subscription tool for developers to automate repetitive tasks",
            "problem": "Developers waste hours on manual tasks",
            "target_user": "Software developers",
            "monetization_model": "subscription",
            "competition_level": "low",
            "difficulty": "easy",
            "time_to_revenue": "weeks",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["validation_passed"] is True
        assert data["total_score"] > 0
        assert data["score_decision"]
        assert data["final_decision"] in {"APPROVED", "HOLD", "REJECTED"}
        assert data["offer"]
        assert data["distribution"]
        assert data["next_step"]
        assert data["pipeline_stage"]

    def test_analyze_minimal_idea(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "A subscription marketplace for freelancers to find paid gigs with pricing tiers",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] >= 0

    def test_analyze_rejects_no_demand(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "Something vague without any context",
            "problem": "",
            "target_user": "",
        })
        assert resp.status_code == 200
        data = resp.json()
        # Should either reject at validation or scoring
        assert data["final_decision"] in {"REJECTED", "HOLD"}

    def test_analyze_empty_idea_fails(self) -> None:
        resp = client.post("/api/analyze/", json={"idea": ""})
        assert resp.status_code == 422  # Validation error

    def test_analyze_returns_score_breakdown(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "SaaS subscription tool for users",
            "problem": "Users need better tools",
            "target_user": "Business users",
            "monetization_model": "subscription",
        })
        data = resp.json()
        if data["validation_passed"]:
            assert "demand" in data["score_breakdown"]
            assert "monetization" in data["score_breakdown"]
            assert len(data["score_dimensions"]) == 5

    def test_analyze_returns_offer(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "Task management subscription SaaS for developers",
            "problem": "Developers need task tracking",
            "target_user": "Software developers",
            "monetization_model": "subscription",
        })
        data = resp.json()
        if data["validation_passed"]:
            offer = data["offer"]
            assert offer.get("pricing") or offer.get("rejection_reason")

    def test_analyze_returns_distribution(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "SaaS subscription for developer productivity",
            "problem": "Time management",
            "target_user": "Software developers",
            "monetization_model": "subscription",
        })
        data = resp.json()
        if data["validation_passed"]:
            dist = data["distribution"]
            assert dist.get("primary_channel") or dist.get("rejection_reason")

    def test_health_still_works(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_analyze_high_competition_weak_diff_rejected(self) -> None:
        resp = client.post("/api/analyze/", json={
            "idea": "Another project management tool with subscription pricing",
            "problem": "Project management is hard for users",
            "target_user": "Business teams",
            "monetization_model": "subscription",
            "competition_level": "high",
            "differentiation": "",
        })
        data = resp.json()
        assert data["final_decision"] == "REJECTED"
        assert any("saturation" in r.lower() for r in data["validation_blocking"])
