"""
Factory orchestrator for BuildBrief -> repo -> deploy execution.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.factory.build_brief_validator import validate_build_brief
from app.factory.models import BuildBrief, FactoryRunResult, FactoryRunStatus
from app.integrations.github_client import GitHubClient
from app.integrations.vercel_client import VercelClient


def _utcnow_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class FactoryRunStore:
    """In-memory store for factory runs and idempotency records.

    This is a Phase 1 implementation that enables deterministic retries.
    The interface is intentionally small so it can be replaced by SQLite in Phase 2.
    """

    def __init__(self) -> None:
        self._runs_by_id: dict[str, FactoryRunResult] = {}
        self._runs_by_idempotency_key: dict[str, str] = {}

    def reset(self) -> None:
        """Clear all in-memory run data (used by tests)."""
        self._runs_by_id.clear()
        self._runs_by_idempotency_key.clear()

    def get_by_run_id(self, run_id: str) -> FactoryRunResult | None:
        """Return a run by ID."""
        run = self._runs_by_id.get(run_id)
        if run is None:
            return None
        return run.model_copy(deep=True)

    def get_by_idempotency_key(self, key: str) -> FactoryRunResult | None:
        """Return the run mapped to an idempotency key."""
        run_id = self._runs_by_idempotency_key.get(key)
        if run_id is None:
            return None
        return self.get_by_run_id(run_id)

    def upsert(self, run: FactoryRunResult) -> None:
        """Persist a run and maintain idempotency mapping."""
        self._runs_by_id[run.run_id] = run.model_copy(deep=True)
        self._runs_by_idempotency_key[run.idempotency_key] = run.run_id

    def list_runs(self) -> list[FactoryRunResult]:
        """Return a defensive copy of all runs in the store."""
        return [run.model_copy(deep=True) for run in self._runs_by_id.values()]


class FactoryOrchestrator:
    """Coordinates BuildBrief validation, repo creation, and deployment."""

    def __init__(
        self,
        *,
        github_client: GitHubClient,
        vercel_client: VercelClient,
        run_store: FactoryRunStore | None = None,
        github_owner: str = "ai-dan",
        repo_template: str = "saas-template",
    ) -> None:
        self._github_client = github_client
        self._vercel_client = vercel_client
        self._store = run_store or FactoryRunStore()
        self._github_owner = github_owner
        self._repo_template = repo_template

    @property
    def store(self) -> FactoryRunStore:
        """Expose the run store for read access and tests."""
        return self._store

    def get_run(self, run_id: str) -> FactoryRunResult | None:
        """Get a run by ID."""
        return self._store.get_by_run_id(run_id)

    def run_factory_build(self, build_brief: BuildBrief, dry_run: bool) -> FactoryRunResult:
        """Execute a factory build with idempotency and dry-run support.

        Behavior:
        - Validate BuildBrief contract.
        - Replay existing succeeded/running run when idempotency key matches.
        - In dry-run mode, emit deterministic preview URLs with no side effects.
        - In live mode, create repo from template, inject PRODUCT_BRIEF.md + product.config.json,
          and trigger Vercel deployment.
        """
        validation = validate_build_brief(build_brief)
        if not validation.valid:
            return FactoryRunResult(
                run_id=str(uuid.uuid4()),
                project_id=build_brief.project_id,
                idea_id=build_brief.idea_id,
                status=FactoryRunStatus.FAILED,
                idempotency_key=build_brief.idempotency_key(),
                dry_run=dry_run,
                error="; ".join(validation.errors),
                events=[
                    {
                        "timestamp": _utcnow_iso(),
                        "step": "validate_build_brief",
                        "status": "failed",
                        "details": {"errors": validation.errors},
                    },
                ],
            )

        idempotency_key = build_brief.idempotency_key()
        existing = self._store.get_by_idempotency_key(idempotency_key)
        if existing and existing.status in (FactoryRunStatus.RUNNING, FactoryRunStatus.SUCCEEDED):
            replayed = existing.model_copy(deep=True)
            replayed.events.append(
                {
                    "timestamp": _utcnow_iso(),
                    "step": "idempotency_replay",
                    "status": "ok",
                    "details": {"replayed_run_id": existing.run_id},
                },
            )
            replayed.updated_at = _utcnow_iso()
            self._store.upsert(replayed)
            return replayed

        run = FactoryRunResult(
            run_id=str(uuid.uuid4()),
            project_id=build_brief.project_id,
            idea_id=build_brief.idea_id,
            status=FactoryRunStatus.RUNNING,
            idempotency_key=idempotency_key,
            dry_run=dry_run,
            stub=True,
        )
        run.events.append(
            {
                "timestamp": _utcnow_iso(),
                "step": "validate_build_brief",
                "status": "ok",
                "details": {
                    "brief_hash": build_brief.brief_hash(),
                    "idempotency_key": idempotency_key,
                },
            },
        )
        self._store.upsert(run)

        try:
            repo_name = self._repo_name_for_brief(build_brief)

            if dry_run:
                run.repo_url = f"dry-run://github/{self._github_owner}/{repo_name}"
                run.deploy_url = f"dry-run://vercel/{build_brief.project_id}"
                run.events.extend(
                    [
                        {
                            "timestamp": _utcnow_iso(),
                            "step": "create_repo",
                            "status": "ok",
                            "details": {"repo_name": repo_name, "mode": "dry_run"},
                        },
                        {
                            "timestamp": _utcnow_iso(),
                            "step": "inject_files",
                            "status": "ok",
                            "details": {
                                "files": ["PRODUCT_BRIEF.md", "product.config.json"],
                                "mode": "dry_run",
                            },
                        },
                        {
                            "timestamp": _utcnow_iso(),
                            "step": "trigger_deploy",
                            "status": "ok",
                            "details": {"target": "vercel", "mode": "dry_run"},
                        },
                    ],
                )
                run.status = FactoryRunStatus.SUCCEEDED
                run.updated_at = _utcnow_iso()
                self._store.upsert(run)
                return run

            repo = self._github_client.create_repo_from_template(
                owner=self._github_owner,
                name=repo_name,
                template_owner=self._github_owner,
                template_repo=self._repo_template,
                private=True,
                description=build_brief.hypothesis,
            )
            run.repo_url = repo.get("html_url")
            run.events.append(
                {
                    "timestamp": _utcnow_iso(),
                    "step": "create_repo",
                    "status": "ok",
                    "details": {"repo_full_name": repo.get("full_name")},
                },
            )

            brief_md = build_brief.to_product_brief_markdown()
            product_config = json.dumps(
                {
                    "project_id": build_brief.project_id,
                    "idea_id": build_brief.idea_id,
                    "deployment_target": build_brief.deployment_target,
                    "cta": build_brief.cta,
                    "pricing_hint": build_brief.pricing_hint,
                    "mvp_scope": build_brief.mvp_scope,
                    "acceptance_criteria": build_brief.acceptance_criteria,
                    "landing_page_requirements": build_brief.landing_page_requirements,
                    "feature_flags": build_brief.feature_flags,
                },
                indent=2,
                sort_keys=True,
            )

            self._github_client.upsert_file(
                owner=self._github_owner,
                repo=repo_name,
                path="PRODUCT_BRIEF.md",
                content=brief_md,
                message=f"factory: add PRODUCT_BRIEF for {build_brief.project_id}",
            )
            self._github_client.upsert_file(
                owner=self._github_owner,
                repo=repo_name,
                path="product.config.json",
                content=product_config,
                message=f"factory: add product config for {build_brief.project_id}",
            )
            run.events.append(
                {
                    "timestamp": _utcnow_iso(),
                    "step": "inject_files",
                    "status": "ok",
                    "details": {"files": ["PRODUCT_BRIEF.md", "product.config.json"]},
                },
            )

            project = self._vercel_client.ensure_project(name=repo_name)
            deployment = self._vercel_client.deploy_repo(
                project_name=repo_name,
                repo_url=run.repo_url or f"https://github.com/{self._github_owner}/{repo_name}",
                metadata={"project_id": build_brief.project_id, "run_id": run.run_id},
            )
            run.deploy_url = deployment["deploy_url"]
            run.events.append(
                {
                    "timestamp": _utcnow_iso(),
                    "step": "trigger_deploy",
                    "status": "ok",
                    "details": {
                        "deployment_id": deployment.get("deployment_id"),
                        "project_id": project.get("project_id"),
                    },
                },
            )

            run.status = FactoryRunStatus.SUCCEEDED
            run.stub = bool(repo.get("stub", True) or deployment.get("stub", True))
            run.updated_at = _utcnow_iso()
            self._store.upsert(run)
            return run
        except Exception as exc:  # pragma: no cover - defensive final guard
            run.status = FactoryRunStatus.FAILED
            run.error = str(exc)
            run.updated_at = _utcnow_iso()
            run.events.append(
                {
                    "timestamp": _utcnow_iso(),
                    "step": "orchestration",
                    "status": "failed",
                    "details": {"error": str(exc)},
                },
            )
            self._store.upsert(run)
            return run

    def list_runs(self) -> list[FactoryRunResult]:
        """Return all tracked factory runs, newest first."""
        runs = self._store.list_runs()
        runs.sort(key=lambda item: item.created_at, reverse=True)
        return runs

    @staticmethod
    def _repo_name_for_brief(build_brief: BuildBrief) -> str:
        """Generate deterministic repo names from project ID."""
        base = build_brief.project_id.lower().replace("_", "-").replace(" ", "-")
        cleaned = "".join(ch for ch in base if ch.isalnum() or ch == "-").strip("-")
        if not cleaned:
            raise ValueError("project_id does not produce a valid repository name.")
        return cleaned
