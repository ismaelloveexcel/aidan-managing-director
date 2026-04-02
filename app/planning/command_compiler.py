"""
command_compiler.py – Translates plans into structured commands.

Converts high-level plans produced by the planner into concrete,
dispatchable command objects for downstream systems.  This module
contains **no execution logic** – it only builds command payloads.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

_REQUIRED_COMMAND_FIELDS = {"action", "parameters"}

_KNOWN_ACTIONS = frozenset(
    {
        "create_repo",
        "setup_project",
        "implement_core",
        "add_tests",
        "deploy",
        "setup_monetization",
        "launch_marketing",
    },
)


class Command(BaseModel):
    """A single structured command ready for dispatch."""

    command_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    source_plan_id: str | None = None
    source_step_id: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _step_to_command(
    step: dict[str, Any],
    plan_id: str | None = None,
    idea_name: str | None = None,
) -> dict[str, Any]:
    """Convert a single plan step into a :class:`Command` dict."""
    parameters: dict[str, Any] = {
        "description": step.get("description", ""),
    }
    if idea_name:
        parameters["project_name"] = idea_name

    command = Command(
        action=step["action"],
        parameters=parameters,
        priority=step.get("priority", "medium"),
        source_plan_id=plan_id,
        source_step_id=step.get("step_id"),
    )
    return command.model_dump()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_commands(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Compile all steps of a plan into a list of structured commands.

    Args:
        plan: A plan dictionary as returned by
              :func:`app.planning.planner.create_plan`.  Must contain
              ``steps`` (list) and ``plan_id`` (str).

    Returns:
        An ordered list of command dictionaries, one per plan step.

    Raises:
        ValueError: If the plan is missing required fields.
    """
    if "steps" not in plan:
        raise ValueError("Plan must contain a 'steps' field.")

    plan_id = plan.get("plan_id")
    idea_name = plan.get("idea_name")

    return [
        _step_to_command(step, plan_id=plan_id, idea_name=idea_name)
        for step in plan["steps"]
    ]


class CommandCompiler:
    """Compiles structured commands from abstract plan representations."""

    def compile(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Compile a single plan step into a structured command payload.

        Args:
            plan: A single plan-step representation.

        Returns:
            A command dictionary ready for dispatch.
        """
        return _step_to_command(plan)

    def compile_batch(self, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compile multiple plan steps into a list of command payloads.

        Args:
            plans: List of plan-step representations.

        Returns:
            A list of command dictionaries ready for dispatch.
        """
        return [self.compile(p) for p in plans]

    def validate(self, command: dict[str, Any]) -> bool:
        """Validate a compiled command before it is dispatched.

        A command is considered valid when it contains the required
        fields (``action`` and ``parameters``) and its ``action`` is a
        recognised action type.

        Args:
            command: The command dictionary to validate.

        Returns:
            True if the command is valid, False otherwise.
        """
        if not _REQUIRED_COMMAND_FIELDS.issubset(command):
            return False
        if command.get("action") not in _KNOWN_ACTIONS:
            return False
        return True
