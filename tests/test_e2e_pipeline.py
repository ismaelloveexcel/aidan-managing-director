"""End-to-end pipeline tests for the three mandatory scenarios.

Each test fires a single request at the chat endpoint and asserts the
full mandatory response format is returned with no placeholders.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Mandatory response fields
# ---------------------------------------------------------------------------
_MANDATORY_KEYS = {"summary", "decision", "score", "risks", "suggested_next_action", "commands"}
_SCORE_KEYS = {"feasibility", "profitability", "speed", "competition", "aggregate"}


def _assert_pipeline_response(body: dict) -> None:
    """Verify that *body* conforms to the mandatory pipeline format."""
    for key in _MANDATORY_KEYS:
        assert key in body, f"Missing mandatory key: {key}"

    # Score must be a dict with all sub-keys when present.
    if body["score"] is not None:
        for key in _SCORE_KEYS:
            assert key in body["score"], f"Missing score key: {key}"
            assert isinstance(body["score"][key], (int, float))

    # Risks must be a list of objects with required risk fields.
    assert isinstance(body["risks"], list)
    for risk in body["risks"]:
        assert "description" in risk
        assert "severity" in risk
        assert "mitigation" in risk

    # Commands must be a list of objects with an action field.
    assert isinstance(body["commands"], list)
    for cmd in body["commands"]:
        assert "action" in cmd
        assert "parameters" in cmd

    # No placeholder strings allowed.
    assert body["summary"] and "..." not in body["summary"]
    assert body["decision"] and "..." not in body["decision"]
    assert body["suggested_next_action"] and "..." not in body["suggested_next_action"]


class TestEndToEndPipeline:
    """Mandatory end-to-end scenarios from the issue specification."""

    def test_saas_for_freelancers(self) -> None:
        """Scenario: 'I want a SaaS for freelancers'."""
        resp = client.post("/chat/", json={"message": "I want a SaaS for freelancers"})
        assert resp.status_code == 200
        body = resp.json()
        _assert_pipeline_response(body)

        # Should detect a BUILD or EXPLORE intent (SaaS → build keyword).
        assert body["strategy"]["intent"] in ("build", "explore")
        # Score must be present for actionable intents.
        assert body["score"] is not None
        assert len(body["commands"]) > 0

    def test_business_ideas_in_mauritius(self) -> None:
        """Scenario: 'Give me business ideas in Mauritius'."""
        resp = client.post(
            "/chat/",
            json={"message": "Give me business ideas in Mauritius"},
        )
        assert resp.status_code == 200
        body = resp.json()
        _assert_pipeline_response(body)

        # 'ideas' keyword → EXPLORE intent.
        assert body["strategy"]["intent"] == "explore"
        assert body["score"] is not None
        assert len(body["commands"]) > 0

    def test_evaluate_ai_cv_tool(self) -> None:
        """Scenario: 'Evaluate this idea: AI CV tool'."""
        resp = client.post(
            "/chat/",
            json={"message": "Evaluate this idea: AI CV tool"},
        )
        assert resp.status_code == 200
        body = resp.json()
        _assert_pipeline_response(body)

        # Contains both 'evaluate' and 'idea' → EXPLORE intent.
        assert body["strategy"]["intent"] == "explore"
        assert body["score"] is not None
        assert len(body["risks"]) > 0
        assert len(body["commands"]) > 0
