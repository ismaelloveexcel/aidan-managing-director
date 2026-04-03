"""Streamlit UI for the AI-DAN Command Center."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
import streamlit as st

DEFAULT_BACKEND_URL = os.getenv("AIDAN_BACKEND_URL", "http://localhost:8000")
MAX_HISTORY = 5


def _post_chat(backend_url: str, message: str) -> dict[str, Any]:
    """Send a chat request to the AI-DAN backend."""
    url = f"{backend_url.rstrip('/')}/chat/"
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json={"message": message})
        response.raise_for_status()
        return response.json()


def _fmt_score(value: float | None) -> str:
    """Format a 0-1 score as a friendly percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _render_response(
    response: dict[str, Any],
    *,
    show_technical_details: bool,
    include_header: bool = True,
) -> None:
    """Render a structured AI-DAN response in a friendly layout."""
    if include_header:
        st.subheader("AI-DAN Decision")

    st.markdown("**Summary**")
    st.write(response.get("summary", "No summary available."))

    st.markdown("**Decision**")
    st.info(response.get("decision", "No decision available."))

    score = response.get("score")
    st.markdown("**Score**")
    if score:
        score_cols = st.columns(5)
        score_cols[0].metric("Overall", _fmt_score(score.get("aggregate")))
        score_cols[1].metric("Feasibility", _fmt_score(score.get("feasibility")))
        score_cols[2].metric("Profitability", _fmt_score(score.get("profitability")))
        score_cols[3].metric("Speed", _fmt_score(score.get("speed")))
        score_cols[4].metric("Competition", _fmt_score(score.get("competition")))
    else:
        st.write("Not scored yet.")

    st.markdown("**Risks**")
    risks = response.get("risks", [])
    if risks:
        for risk in risks:
            description = risk.get("description", "Unspecified risk")
            severity = str(risk.get("severity", "unknown")).upper()
            mitigation = risk.get("mitigation", "No mitigation provided.")
            st.markdown(f"- **{severity}** — {description}  \n  _Mitigation:_ {mitigation}")
    else:
        st.write("No major risks identified.")

    st.markdown("**Suggested Next Action**")
    st.success(response.get("suggested_next_action", "No suggestion available."))

    commands = response.get("commands", [])
    with st.expander(f"Commands ({len(commands)})", expanded=False):
        if not commands:
            st.write("No commands generated.")
        for index, command in enumerate(commands, start=1):
            action = command.get("action", "unknown_action")
            priority = command.get("priority", "medium")
            st.markdown(f"{index}. **{action}** (priority: `{priority}`)")
            parameters = command.get("parameters", {})
            if parameters:
                for key, value in parameters.items():
                    st.caption(f"{key}: {value}")

    if show_technical_details:
        with st.expander("Technical Details", expanded=False):
            st.markdown("**Strategy**")
            st.json(response.get("strategy", {}))
            st.markdown("**Raw Response**")
            st.json(response)


def _add_to_history(message: str, response: dict[str, Any]) -> None:
    """Persist the latest interaction in session state."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message": message,
        "response": response,
    }
    st.session_state.history.insert(0, record)
    st.session_state.history = st.session_state.history[:MAX_HISTORY]


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title="AI-DAN Command Center",
        page_icon="🧭",
        layout="centered",
    )
    st.title("AI-DAN Command Center")
    st.caption("Type your idea, get a clear decision, and see next steps.")

    if "history" not in st.session_state:
        st.session_state.history = []

    with st.expander("Settings", expanded=False):
        backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
        show_technical_details = st.toggle("Show technical details", value=False)

    with st.form("ask_aidan"):
        prompt = st.text_area(
            "Ask AI-DAN",
            placeholder="Example: I want a SaaS for freelancers",
            height=100,
        )
        submitted = st.form_submit_button(
            "Get Decision",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            st.warning("Please enter a request for AI-DAN.")
        else:
            try:
                with st.spinner("AI-DAN is analyzing your request..."):
                    response = _post_chat(backend_url, clean_prompt)
                st.session_state.latest_response = response
                st.session_state.latest_prompt = clean_prompt
                _add_to_history(clean_prompt, response)
            except httpx.HTTPStatusError as exc:
                st.error(
                    "AI-DAN returned an error. "
                    f"Status {exc.response.status_code}: {exc.response.text}"
                )
            except httpx.RequestError:
                st.error(
                    "Cannot reach the backend. Make sure FastAPI is running and the URL is correct."
                )
            except Exception as exc:  # pragma: no cover - defensive fallback
                st.error(f"Unexpected error: {exc}")

    latest_response = st.session_state.get("latest_response")
    if latest_response:
        _render_response(
            latest_response,
            show_technical_details=show_technical_details,
            include_header=True,
        )

    if st.session_state.history:
        st.subheader("Recent Interactions")
        for entry in st.session_state.history:
            title = entry["message"][:70]
            with st.expander(f"{title}", expanded=False):
                st.caption(entry["timestamp"])
                st.markdown("**Decision**")
                st.write(entry["response"].get("decision", "No decision available."))
                st.markdown("**Suggested Next Action**")
                st.write(
                    entry["response"].get(
                        "suggested_next_action",
                        "No next action available.",
                    ),
                )


if __name__ == "__main__":
    main()
