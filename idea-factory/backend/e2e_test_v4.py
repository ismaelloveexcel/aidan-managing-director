"""
e2e_test_v4.py — End-to-end tests for Idea Factory v4 API.
Run with: pytest e2e_test_v4.py -v

These tests hit the real endpoints. Start the server first:
  uvicorn main:app --reload
"""

import json
import pytest
import httpx

BASE = "http://localhost:8000"


def test_health():
    r = httpx.get(f"{BASE}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_empty_idea():
    r = httpx.post(f"{BASE}/api/analyze", json={"idea": ""})
    assert r.status_code == 400


def test_analyze_too_short():
    r = httpx.post(f"{BASE}/api/analyze", json={"idea": "short idea"})
    assert r.status_code == 400
    assert "detail" in r.json()


def test_analyze_streams_events():
    """Verify the SSE stream emits at least a result event for a real idea."""
    idea = (
        "A SaaS tool that helps solo freelance developers automatically "
        "generate client invoices from their git commit history, "
        "targeting developers who bill hourly."
    )
    events = []
    with httpx.stream("POST", f"{BASE}/api/analyze", json={"idea": idea}, timeout=120) as resp:
        assert resp.status_code == 200
        buf = ""
        for chunk in resp.iter_text():
            buf += chunk
            parts = buf.split("\n\n")
            buf = parts.pop()
            for part in parts:
                lines = part.split("\n")
                name, data_str = "message", ""
                for line in lines:
                    if line.startswith("event:"):
                        name = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                if data_str:
                    events.append((name, json.loads(data_str)))

    event_names = [e[0] for e in events]
    assert "result" in event_names, f"Expected 'result' event, got: {event_names}"

    result_data = next(d for n, d in events if n == "result")
    assert "score" in result_data
    assert "final_decision" in result_data
    assert result_data["final_decision"] in ("GO", "SKIP", "KILL")
    assert "fastest_revenue" in result_data
    assert "global_viability" in result_data
    assert "best_launch_market" in result_data


def test_chat_single_turn():
    """Chat endpoint returns a reply and updated state."""
    payload = {
        "messages": [{"role": "user", "content": "I want to build an app for dog owners."}],
        "state": {},
    }
    r = httpx.post(f"{BASE}/api/chat", json=payload, timeout=60)
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body
    assert "state" in body
    assert isinstance(body["is_complete"], bool)
    assert body["state"].get("turns", 0) == 1


def test_chat_completes_at_turn_8():
    """After 8 turns the endpoint should return is_complete=True and a final_result."""
    msgs = [{"role": "user", "content": "My idea is an AI scheduling tool for dentists."}]
    state: dict = {"turns": 7}  # one more will push it to 8 → complete
    payload = {"messages": msgs, "state": state}
    r = httpx.post(f"{BASE}/api/chat", json=payload, timeout=90)
    assert r.status_code == 200
    body = r.json()
    assert body["is_complete"] is True
    assert body.get("final_result") is not None
    fr = body["final_result"]
    assert "final_decision" in fr
    assert "score" in fr
    assert "fastest_revenue" in fr


def test_graveyard_page():
    r = httpx.get(f"{BASE}/graveyard")
    assert r.status_code == 200
    assert "Graveyard" in r.text


def test_leaderboard_page():
    r = httpx.get(f"{BASE}/leaderboard")
    assert r.status_code == 200
    assert "Leaderboard" in r.text


def test_public_idea_not_found():
    r = httpx.get(f"{BASE}/idea/999999")
    assert r.status_code == 404
