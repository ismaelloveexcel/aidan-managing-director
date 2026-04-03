"""
project_request.py – Produces GitHub-ready request payloads for approved projects.

When an idea has been evaluated, critiqued, and approved, this module
translates the approved project into a structured request that the
GitHub Factory layer can consume.  No execution logic lives here –
only payload construction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.integrations.github_client import (
    GitHubClient,
    IssueBundleRequest,
    RepoRequest,
)
from app.planning.command_compiler import Command


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProjectRequestPayload(BaseModel):
    """Full payload sent to the GitHub Factory for a new project."""

    project_name: str = Field(description="Human-readable project name.")
    repo_request: RepoRequest = Field(
        description="RepoRequest for the repository.",
    )
    issue_bundle: IssueBundleRequest = Field(
        description="IssueBundleRequest with initial issues.",
    )
    command: Command = Field(
        description="Command for downstream dispatch.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert a human-readable string into a URL-safe slug.

    Lowercases, replaces spaces with hyphens, and strips characters
    that are not alphanumeric or hyphens.
    """
    slug = text.lower().replace(" ", "-")
    return "".join(ch for ch in slug if ch.isalnum() or ch == "-").strip("-")


def _repo_name_from_idea(idea_name: str) -> str:
    """Derive a repository name from an idea title."""
    return _slugify(idea_name)


def _default_issues_for_project(idea_name: str, description: str) -> list[dict[str, Any]]:
    """Generate a starter set of issues for a new project repository."""
    return [
        {
            "title": f"Set up project scaffold for {idea_name}",
            "body": f"Initialise the repository structure for **{idea_name}**.\n\n{description}",
            "labels": ["setup", "priority:high"],
        },
        {
            "title": "Implement core product logic",
            "body": "Build the core product logic as defined in the project plan.",
            "labels": ["feature", "priority:high"],
        },
        {
            "title": "Add initial test suite",
            "body": "Write unit and integration tests for the core functionality.",
            "labels": ["testing", "priority:medium"],
        },
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_project_request(
    idea: dict[str, Any],
    *,
    owner: str = "ai-dan",
    private: bool = True,
    github_client: GitHubClient | None = None,
) -> dict[str, Any]:
    """Build a complete GitHub Factory request payload for an approved idea.

    Takes an idea dictionary (as produced by the idea engine or passed
    through the planner) and returns a :class:`ProjectRequestPayload`
    containing the repository request, an initial issue bundle, and a
    ``create_project_repo`` command.

    Args:
        idea: Must contain ``name`` (str) and ``description`` (str).
              Optional keys: ``target_user``, ``monetization_path``,
              ``difficulty``, ``time_to_launch``.
        owner: Repository owner or organisation.
        private: Whether the new repository should be private.
        github_client: Optional pre-configured :class:`GitHubClient`.
                       When omitted, a client is created from
                       :func:`app.core.config.get_settings`.

    Returns:
        Serialised :class:`ProjectRequestPayload` dictionary.

    Raises:
        ValueError: If required fields are missing from *idea*.
    """
    name = idea.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("Idea must contain a non-empty 'name' string.")
    description = idea.get("description", "")
    if not description or not isinstance(description, str):
        raise ValueError("Idea must contain a non-empty 'description' string.")

    if github_client is None:
        settings = get_settings()
        client = GitHubClient(
            token=settings.github_token,
            base_url=settings.github_api_base_url,
        )
    else:
        client = github_client

    repo_name = _repo_name_from_idea(name)
    if not repo_name:
        raise ValueError(
            f"Idea name {name!r} does not produce a valid repository slug.",
        )

    # Collect optional topics from idea metadata.
    topics: list[str] = []
    target_user = idea.get("target_user")
    if isinstance(target_user, str) and target_user.strip():
        topics.append(_slugify(target_user))
    if idea.get("monetization_path"):
        topics.append("monetised")
    topics = list(dict.fromkeys(topic for topic in topics if topic))

    repo_request = client.prepare_repo_request(
        name=repo_name,
        owner=owner,
        description=description,
        private=private,
        topics=topics,
    )

    issues = _default_issues_for_project(name, description)
    issue_bundle = client.create_issue_bundle(
        owner=owner,
        repo=repo_name,
        issues=issues,
    )

    command = Command(
        action="create_project_repo",
        parameters={
            "project_name": name,
            "repo_name": repo_name,
            "owner": owner,
            "private": private,
            "description": description,
        },
        priority="high",
    )

    payload = ProjectRequestPayload(
        project_name=name,
        repo_request=RepoRequest(**repo_request),
        issue_bundle=IssueBundleRequest(**issue_bundle),
        command=command,
    )

    return payload.model_dump()
