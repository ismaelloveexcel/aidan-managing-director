"""
vercel_client.py - Vercel deployment integration for the GitHub Factory.

This module currently provides deterministic stub behavior so the factory
orchestrator can be built and tested before live Vercel credentials are wired.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class VercelProjectResult(BaseModel):
    """Result payload for create/get project operations."""

    project_id: str
    name: str
    url: str
    stub: bool = True


class VercelDeployResult(BaseModel):
    """Result payload for deployment trigger operations."""

    deployment_id: str
    deploy_url: str
    state: str = "READY"
    stub: bool = True


class VercelClient:
    """Minimal client wrapper for Vercel project and deploy APIs."""

    def __init__(self, token: str, team_id: str | None = None) -> None:
        self.token = token
        self.team_id = team_id

    def ensure_project(self, *, name: str) -> dict[str, Any]:
        """Create or fetch a Vercel project by name.

        Stub behavior always returns a deterministic-like project URL.
        """
        result = VercelProjectResult(
            project_id=f"prj_{uuid.uuid4().hex[:12]}",
            name=name,
            url=f"https://{name}.vercel.app",
            stub=True,
        )
        return result.model_dump()

    def deploy_git_repo(
        self,
        *,
        project_name: str,
        git_repo_full_name: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Trigger deployment from a Git repository.

        Stub behavior returns a fake deployment URL.
        """
        deployment_id = f"dpl_{uuid.uuid4().hex[:12]}"
        result = VercelDeployResult(
            deployment_id=deployment_id,
            deploy_url=f"https://{project_name}-{deployment_id}.vercel.app",
            state="READY",
            stub=True,
        )
        return result.model_dump()

    def deploy_repo(
        self,
        *,
        project_name: str,
        repo_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """High-level deploy helper used by the factory orchestrator.

        The current implementation is stubbed and derives the git repo name from
        the repository URL for traceability in returned metadata.
        """
        _ = metadata or {}
        repo_name = repo_url.rstrip("/").split("/")[-2:]
        git_repo_full_name = "/".join(repo_name) if len(repo_name) == 2 else repo_url
        return self.deploy_git_repo(
            project_name=project_name,
            git_repo_full_name=git_repo_full_name,
        )
