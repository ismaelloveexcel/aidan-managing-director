"""
vercel_client.py - Vercel deployment integration for the GitHub Factory.

Makes real Vercel REST API calls when a token is configured.
Falls back to deterministic stub behavior when no token is set,
so the factory orchestrator can be built and tested without credentials.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_VERCEL_BASE_URL = "https://api.vercel.com"


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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _params(self) -> dict[str, str]:
        if self.team_id:
            return {"teamId": self.team_id}
        return {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_project(self, *, name: str) -> dict[str, Any]:
        """Create or fetch a Vercel project by name.

        Makes real API calls when ``self.token`` is set.
        Falls back to stub behavior on missing token or API error.
        """
        if not self.token:
            return self._stub_project(name)

        try:
            with httpx.Client(timeout=30) as client:
                # Try to fetch existing project first
                resp = client.get(
                    f"{_VERCEL_BASE_URL}/v9/projects/{name}",
                    headers=self._headers(),
                    params=self._params(),
                )
                if resp.status_code == 200:
                    project = resp.json()
                    return VercelProjectResult(
                        project_id=project["id"],
                        name=project["name"],
                        url=f"https://{project['name']}.vercel.app",
                        stub=False,
                    ).model_dump()

                if resp.status_code == 404:
                    # Project doesn't exist — create it
                    create_resp = client.post(
                        f"{_VERCEL_BASE_URL}/v10/projects",
                        headers=self._headers(),
                        params=self._params(),
                        json={"name": name, "framework": "nextjs"},
                    )
                    create_resp.raise_for_status()
                    project = create_resp.json()
                    return VercelProjectResult(
                        project_id=project["id"],
                        name=project["name"],
                        url=f"https://{project['name']}.vercel.app",
                        stub=False,
                    ).model_dump()

                resp.raise_for_status()

        except Exception as exc:
            logger.warning("Vercel ensure_project failed, using stub: %s", exc)

        return self._stub_project(name)

    def deploy_git_repo(
        self,
        *,
        project_name: str,
        git_repo_full_name: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Trigger a Vercel deployment from a GitHub repository.

        Makes a real API call when ``self.token`` is set.
        Falls back to stub behavior on missing token or API error.
        """
        if not self.token:
            return self._stub_deploy(project_name)

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{_VERCEL_BASE_URL}/v13/deployments",
                    headers=self._headers(),
                    params=self._params(),
                    json={
                        "name": project_name,
                        "gitSource": {
                            "type": "github",
                            "repoId": git_repo_full_name,
                            "ref": branch,
                        },
                    },
                )
                resp.raise_for_status()
                dep = resp.json()
                return VercelDeployResult(
                    deployment_id=dep["uid"],
                    deploy_url=dep.get("url", f"{project_name}.vercel.app"),
                    state=dep.get("readyState", "BUILDING"),
                    stub=False,
                ).model_dump()

        except Exception as exc:
            logger.warning("Vercel deploy_git_repo failed, using stub: %s", exc)

        return self._stub_deploy(project_name)

    def deploy_repo(
        self,
        *,
        project_name: str,
        repo_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """High-level deploy helper used by the factory orchestrator.

        Derives the GitHub repo full name from the repository URL and
        delegates to ``deploy_git_repo``.
        """
        _ = metadata or {}
        repo_parts = repo_url.rstrip("/").split("/")[-2:]
        git_repo_full_name = "/".join(repo_parts) if len(repo_parts) == 2 else repo_url
        return self.deploy_git_repo(
            project_name=project_name,
            git_repo_full_name=git_repo_full_name,
        )

    # ------------------------------------------------------------------
    # Stub helpers
    # ------------------------------------------------------------------

    def _stub_project(self, name: str) -> dict[str, Any]:
        return VercelProjectResult(
            project_id=f"prj_{uuid.uuid4().hex[:12]}",
            name=name,
            url=f"https://{name}.vercel.app",
            stub=True,
        ).model_dump()

    def _stub_deploy(self, project_name: str) -> dict[str, Any]:
        deployment_id = f"dpl_{uuid.uuid4().hex[:12]}"
        return VercelDeployResult(
            deployment_id=deployment_id,
            deploy_url=f"https://{project_name}-{deployment_id}.vercel.app",
            state="READY",
            stub=True,
        ).model_dump()
