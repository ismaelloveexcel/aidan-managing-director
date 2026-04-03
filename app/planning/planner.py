"""
planner.py – Converts evaluated ideas into structured execution plans.

Breaks a high-level idea into discrete, ordered steps that the command
compiler can later translate into dispatchable commands.  No execution
logic lives here – only plan construction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """A single actionable step within a plan."""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    action: str
    description: str
    priority: str = "medium"
    estimated_effort: str = "medium"
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Structured output representing a full execution plan for an idea."""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idea_name: str
    idea_summary: str
    steps: list[PlanStep]
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdeaPlanInput(BaseModel):
    """Validated input payload for plan creation."""

    name: str = Field(min_length=1, description="Idea name.")
    description: str = Field(min_length=1, description="Idea description.")
    target_user: str | None = Field(
        default=None,
        description="Optional target user segment.",
    )
    monetization_path: str | None = Field(
        default=None,
        description="Optional monetization approach.",
    )
    difficulty: str | None = Field(
        default=None,
        description="Optional relative difficulty label.",
    )
    time_to_launch: str | None = Field(
        default=None,
        description="Optional estimated time to launch.",
    )
    marketing_strategy: str | None = Field(
        default=None,
        description="Optional marketing strategy.",
    )


# ---------------------------------------------------------------------------
# Step-generation helpers (pure logic, no side-effects)
# ---------------------------------------------------------------------------

_DEFAULT_STEPS: list[dict[str, Any]] = [
    {
        "action": "create_project_repo",
        "description": "Create the project repository",
        "priority": "high",
        "estimated_effort": "low",
    },
    {
        "action": "setup_project",
        "description": "Scaffold the project structure and install dependencies",
        "priority": "high",
        "estimated_effort": "medium",
    },
    {
        "action": "implement_core",
        "description": "Build core product logic",
        "priority": "high",
        "estimated_effort": "high",
    },
    {
        "action": "add_tests",
        "description": "Write tests for the core functionality",
        "priority": "medium",
        "estimated_effort": "medium",
    },
    {
        "action": "deploy",
        "description": "Deploy the project to production",
        "priority": "medium",
        "estimated_effort": "medium",
    },
]


def _build_steps(idea: dict[str, Any]) -> list[PlanStep]:
    """Derive ordered plan steps from an idea dictionary.

    The base set of steps is always generated.  Additional steps are
    appended when the idea contains recognised optional fields such as
    ``monetization_path`` or ``marketing_strategy``.
    """
    steps: list[PlanStep] = []
    order = 1

    for template in _DEFAULT_STEPS:
        steps.append(
            PlanStep(
                order=order,
                action=template["action"],
                description=template["description"],
                priority=template["priority"],
                estimated_effort=template["estimated_effort"],
                depends_on=[steps[-1].step_id] if steps else [],
            ),
        )
        order += 1

    # Conditional steps based on idea metadata
    if idea.get("monetization_path"):
        steps.append(
            PlanStep(
                order=order,
                action="setup_monetization",
                description=f"Integrate monetization via {idea['monetization_path']}",
                priority="medium",
                estimated_effort="medium",
                depends_on=[steps[-1].step_id] if steps else [],
            ),
        )
        order += 1

    if idea.get("marketing_strategy"):
        steps.append(
            PlanStep(
                order=order,
                action="launch_marketing",
                description="Execute the marketing strategy",
                priority="low",
                estimated_effort="medium",
                depends_on=[steps[-1].step_id] if steps else [],
            ),
        )

    return steps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_plan_model(idea: IdeaPlanInput | dict[str, Any]) -> Plan:
    """Convert an idea payload into a validated :class:`Plan` model."""
    if isinstance(idea, IdeaPlanInput):
        idea_input = idea
    else:
        if not idea.get("name"):
            raise ValueError("Idea must contain a 'name' field.")
        if not idea.get("description"):
            raise ValueError("Idea must contain a 'description' field.")
        idea_input = IdeaPlanInput(
            name=str(idea["name"]),
            description=str(idea["description"]),
            target_user=str(idea["target_user"]) if idea.get("target_user") else None,
            monetization_path=(
                str(idea["monetization_path"]) if idea.get("monetization_path") else None
            ),
            difficulty=str(idea["difficulty"]) if idea.get("difficulty") else None,
            time_to_launch=(
                str(idea["time_to_launch"]) if idea.get("time_to_launch") else None
            ),
            marketing_strategy=(
                str(idea["marketing_strategy"]) if idea.get("marketing_strategy") else None
            ),
        )

    idea_dict = idea_input.model_dump(exclude_none=True)
    steps = _build_steps(idea_dict)

    metadata: dict[str, Any] = {}
    for key in ("target_user", "difficulty", "time_to_launch"):
        value = idea_dict.get(key)
        if value:
            metadata[key] = value

    return Plan(
        idea_name=idea_input.name,
        idea_summary=idea_input.description,
        steps=steps,
        metadata=metadata,
    )


def create_plan(idea: dict[str, Any]) -> dict[str, Any]:
    """Convert an idea dictionary into a structured execution plan.

    Args:
        idea: Must contain at least ``name`` and ``description``.
              Optional keys: ``target_user``, ``monetization_path``,
              ``difficulty``, ``time_to_launch``, ``marketing_strategy``.

    Returns:
        A serialised :class:`Plan` dictionary with ordered steps and
        metadata extracted from the idea.

    Raises:
        ValueError: If required fields are missing from *idea*.
    """
    return create_plan_model(idea).model_dump()
