"""Tests for the founder-to-command flow."""

from fastapi.testclient import TestClient

from app.reasoning.models import (
    CommandOutput,
    FounderResponse,
    IntentType,
)
from app.reasoning.strategist import Strategist
from main import app

client = TestClient(app)


class TestProcessFounderInput:
    """Unit tests for Strategist.process_founder_input."""

    def setup_method(self) -> None:
        self.strategist = Strategist()

    def test_build_intent_returns_founder_response(self) -> None:
        result = self.strategist.process_founder_input("I want to build a SaaS")
        assert isinstance(result, FounderResponse)
        assert result.strategy.intent == IntentType.BUILD

    def test_build_intent_has_commands(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert len(result.commands) > 0
        assert all(isinstance(c, CommandOutput) for c in result.commands)

    def test_build_intent_has_score(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert result.score is not None
        assert 0.0 <= result.score <= 1.0

    def test_build_intent_has_risks(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert len(result.risks) > 0

    def test_build_intent_has_decision(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert len(result.decision) > 0

    def test_build_intent_has_summary(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert len(result.summary) > 0

    def test_build_intent_has_suggested_next_action(self) -> None:
        result = self.strategist.process_founder_input("Build a new product")
        assert len(result.suggested_next_action) > 0

    def test_explore_intent_returns_founder_response(self) -> None:
        result = self.strategist.process_founder_input("Let's brainstorm some ideas")
        assert isinstance(result, FounderResponse)
        assert result.strategy.intent == IntentType.EXPLORE
        assert len(result.commands) > 0

    def test_improve_intent(self) -> None:
        result = self.strategist.process_founder_input("We need to improve our app")
        assert result.strategy.intent == IntentType.IMPROVE
        assert len(result.commands) > 0
        assert result.decision

    def test_monetise_intent(self) -> None:
        result = self.strategist.process_founder_input("How can we monetize this?")
        assert result.strategy.intent == IntentType.MONETISE
        assert len(result.commands) > 0

    def test_pivot_intent(self) -> None:
        result = self.strategist.process_founder_input("We should pivot to a new direction")
        assert result.strategy.intent == IntentType.PIVOT
        assert len(result.risks) > 0

    def test_unknown_intent_asks_for_clarification(self) -> None:
        result = self.strategist.process_founder_input("hello there")
        assert result.strategy.intent == IntentType.UNKNOWN
        assert "clarif" in result.decision.lower() or "clarif" in result.suggested_next_action.lower()

    def test_context_passed_through(self) -> None:
        result = self.strategist.process_founder_input(
            "Build something",
            context={"goals": ["Reach 100 users"]},
        )
        assert "Reach 100 users" in result.strategy.objectives


class TestChatRouteFounderFlow:
    """Integration tests for the chat endpoint with founder flow."""

    def test_chat_returns_founder_response(self) -> None:
        resp = client.post("/chat/", json={"message": "I want to build a SaaS"})
        assert resp.status_code == 200
        body = resp.json()
        assert "founder_response" in body
        fr = body["founder_response"]
        assert "summary" in fr
        assert "decision" in fr
        assert "risks" in fr
        assert "suggested_next_action" in fr
        assert "commands" in fr
        assert "strategy" in fr

    def test_chat_build_has_commands(self) -> None:
        resp = client.post("/chat/", json={"message": "Build a new product"})
        body = resp.json()
        commands = body["founder_response"]["commands"]
        assert len(commands) > 0
        assert all("action" in c for c in commands)

    def test_chat_build_has_score(self) -> None:
        resp = client.post("/chat/", json={"message": "Build a new product"})
        body = resp.json()
        assert body["founder_response"]["score"] is not None

    def test_chat_unknown_has_no_score(self) -> None:
        resp = client.post("/chat/", json={"message": "hello"})
        body = resp.json()
        assert body["founder_response"]["score"] is None

    def test_chat_still_returns_strategy(self) -> None:
        resp = client.post("/chat/", json={"message": "I want to build a SaaS"})
        assert resp.status_code == 200
        body = resp.json()
        assert "strategy" in body
        assert body["strategy"]["intent"] == "build"

    def test_chat_unknown_intent_strategy(self) -> None:
        resp = client.post("/chat/", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.json()["strategy"]["intent"] == "unknown"

    def test_chat_with_context(self) -> None:
        resp = client.post(
            "/chat/",
            json={
                "message": "Build a product",
                "context": {"goals": ["Reach 100 users"]},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        objectives = body["founder_response"]["strategy"]["objectives"]
        assert "Reach 100 users" in objectives

    def test_chat_reply_mentions_intent(self) -> None:
        resp = client.post("/chat/", json={"message": "I want to build a SaaS"})
        body = resp.json()
        assert "build" in body["reply"].lower()

    def test_chat_improve_flow(self) -> None:
        resp = client.post("/chat/", json={"message": "We need to improve our app"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["strategy"]["intent"] == "improve"
        assert len(body["founder_response"]["commands"]) > 0

    def test_chat_monetise_flow(self) -> None:
        resp = client.post("/chat/", json={"message": "How do we monetize?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["strategy"]["intent"] == "monetise"
        assert len(body["founder_response"]["commands"]) > 0

    def test_chat_pivot_flow(self) -> None:
        resp = client.post("/chat/", json={"message": "We need to pivot"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["strategy"]["intent"] == "pivot"
        assert len(body["founder_response"]["risks"]) > 0
