"""
command_compiler.py – Translates plans into structured commands.

Converts high-level plans produced by the planner into concrete,
dispatchable command objects for downstream systems.  This module
contains **no execution logic** – it only builds command payloads.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.planning.approval_gate import requires_approval

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

_REQUIRED_COMMAND_FIELDS = {"action", "parameters"}

_KNOWN_ACTIONS = frozenset(
    {
        "create_repo",
        "create_project_repo",
        "setup_project",
        "implement_core",
        "add_tests",
        "deploy",
        "setup_monetization",
        "launch_marketing",
        "delete_repo",
        "modify_billing",
    },
)

_ACTION_ALIASES: dict[str, str] = {
    "create_repo": "create_project_repo",
}


class Command(BaseModel):
    """A single structured command ready for dispatch."""

    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    command_type: str | None = None
    schema_version: str = "1.0"
    target_system: str = "github_factory"
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    requires_approval: bool = False
    source_plan_id: str | None = None
    source_step_id: str | None = None

    @model_validator(mode="after")
    def _normalise_fields(self) -> Command:
        self.action = _normalise_action(self.action)
        self.command_type = self.action
        if not self.requires_approval:
            self.requires_approval = requires_approval({"action": self.action})
        return self


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _step_to_command(
    step: dict[str, Any],
    plan_id: str | None = None,
    idea_name: str | None = None,
) -> Command:
    """Convert a single plan step into a :class:`Command` model."""
    action = _normalise_action(step["action"])
    parameters: dict[str, Any] = {
        "description": step.get("description", ""),
        "step_order": step.get("order"),
        "estimated_effort": step.get("estimated_effort"),
        "depends_on": step.get("depends_on", []),
    }
    if idea_name:
        parameters["project_name"] = idea_name
    if action == "create_project_repo":
        parameters.setdefault("repo_name", _slugify(idea_name or "project"))
        parameters.setdefault("owner", "ai-dan")
        parameters.setdefault("private", True)

    return Command(
        action=action,
        parameters=parameters,
        priority=step.get("priority", "medium"),
        source_plan_id=plan_id,
        source_step_id=step.get("step_id"),
    )


def _normalise_action(action: str) -> str:
    """Return a canonical action name for downstream systems."""
    return _ACTION_ALIASES.get(action, action)


def _slugify(value: str) -> str:
    """Create a GitHub-safe repo slug from a project name."""
    slug = value.lower().replace(" ", "-")
    cleaned = "".join(ch for ch in slug if ch.isalnum() or ch == "-").strip("-")
    return cleaned or "project"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_commands(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Compile all steps of a plan into a list of structured commands.

    Args:
        plan: A plan dictionary as returned by
              :func:`app.planning.planner.create_plan`.  Must contain
              ``plan_id`` (str) and ``steps`` (list of dicts, each with
              a non-empty ``action`` string).

    Returns:
        An ordered list of command dictionaries, one per plan step.

    Raises:
        ValueError: If the plan is missing required fields or has invalid types.
    """
    command_models = compile_command_models(plan)
    return [command.model_dump() for command in command_models]


def compile_command_models(plan: dict[str, Any]) -> list[Command]:
    """Compile all steps of a plan into typed :class:`Command` models."""
    if "steps" not in plan:
        raise ValueError("Plan must contain a 'steps' field.")

    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        raise ValueError("Plan must contain a non-empty 'plan_id' string.")

    steps = plan["steps"]
    if not isinstance(steps, list):
        raise ValueError("'steps' must be a list of step dictionaries.")

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(
                f"Each step must be a dict; got {type(step).__name__} at index {index}.",
            )
        action = step.get("action")
        if not isinstance(action, str) or not action:
            raise ValueError(
                f"Each step must contain a non-empty 'action' string (index {index}).",
            )
        if _normalise_action(action) not in _KNOWN_ACTIONS:
            raise ValueError(
                f"Unknown action '{action}' at index {index}; update planner/compiler mapping.",
            )

    idea_name = plan.get("idea_name")
    if idea_name is not None and not isinstance(idea_name, str):
        raise ValueError("If provided, 'idea_name' must be a string.")

    return [
        _step_to_command(step, plan_id=plan_id, idea_name=idea_name)
        for step in steps
    ]


class CommandCompiler:
    """Compiles structured commands from abstract plan representations."""

    def compile(
        self,
        step: dict[str, Any],
        *,
        plan_id: str | None = None,
        idea_name: str | None = None,
    ) -> dict[str, Any]:
        """Compile a single plan step into a structured command payload.

        Args:
            step: A single plan-step representation.
            plan_id: Optional plan identifier for provenance tracking.
            idea_name: Optional idea name to include in command parameters.

        Returns:
            A command dictionary ready for dispatch.
        """
        return _step_to_command(
            step,
            plan_id=plan_id,
            idea_name=idea_name,
        ).model_dump()

    def compile_batch(
        self,
        steps: list[dict[str, Any]],
        *,
        plan_id: str | None = None,
        idea_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Compile multiple plan steps into a list of command payloads.

        Args:
            steps: List of plan-step representations.
            plan_id: Optional plan identifier for provenance tracking.
            idea_name: Optional idea name to include in command parameters.

        Returns:
            A list of command dictionaries ready for dispatch.
        """
        return [
            self.compile(s, plan_id=plan_id, idea_name=idea_name) for s in steps
        ]

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
