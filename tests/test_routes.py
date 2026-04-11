"""Tests for reasoning-wired API routes."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestChatRoute:
    """Chat endpoint tests."""

    def test_chat_returns_strategy(self) -> None:
        resp = client.post("/chat/", json={"message": "I want to build a SaaS"})
        assert resp.status_code == 200
        body = resp.json()
        assert "strategy" in body
        assert body["strategy"]["intent"] == "build"

    def test_chat_unknown_intent(self) -> None:
        resp = client.post("/chat/", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.json()["strategy"]["intent"] == "unknown"


class TestIdeasRoutes:
    """Ideas endpoint tests."""

    def test_generate_idea(self) -> None:
        resp = client.post("/ideas/generate", json={"prompt": "healthcare tools"})
        assert resp.status_code == 200
        body = resp.json()
        assert "idea_id" in body
        assert "title" in body
        assert "problem" in body
        assert "monetization_path" in body

    def test_brainstorm(self) -> None:
        resp = client.post(
            "/ideas/brainstorm",
            json={"prompt": "marketing tools", "count": 3},
        )
        assert resp.status_code == 200
        ideas = resp.json()
        assert len(ideas) == 3

    def test_evaluate_idea(self) -> None:
        # First generate an idea
        gen_resp = client.post("/ideas/generate", json={"prompt": "fintech"})
        idea = gen_resp.json()

        resp = client.post("/ideas/evaluate", json={"idea": idea})
        assert resp.status_code == 200
        body = resp.json()
        assert "total_score" in body
        assert "breakdown" in body
        assert "decision" in body

    def test_critique_idea(self) -> None:
        gen_resp = client.post("/ideas/generate", json={"prompt": "fintech"})
        idea = gen_resp.json()

        resp = client.post("/ideas/critique", json={"idea": idea})
        assert resp.status_code == 200
        body = resp.json()
        assert "weaknesses" in body
        assert "risks" in body
        assert "verdict" in body


class TestHealthRoute:
    """Health check still works."""

    def test_health(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in {"ok", "degraded"}
        assert "checks" in data
        assert "version" in data
