"""
factory_client.py - Minimal bridge to dispatch external factory workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.factory.models import BuildBrief, FactoryRunResult
from app.factory.orchestrator import FactoryOrchestrator
from app.integrations.github_client import GitHubClient


def _utcnow_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class FactoryTrackingResult(BaseModel):
    """Parsed workflow/build tracking payload for command surfaces."""

    run_id: str
    workflow_dispatched: bool
    workflow_run_id: str | None = None
    status: str
    repo_url: str | None = None
    deployment_url: str | None = None
    tracked_at: str = Field(default_factory=_utcnow_iso)


class FactoryClient:
    """Dispatches factory workflow and returns tracked build status."""

    def __init__(
        self,
        *,
        github_client: GitHubClient,
        orchestrator: FactoryOrchestrator,
        factory_owner: str,
        factory_repo: str,
        workflow_id: str,
    ) -> None:
        self._github_client = github_client
        self._orchestrator = orchestrator
        self._factory_owner = factory_owner
        self._factory_repo = factory_repo
        self._workflow_id = workflow_id

    def trigger_build(
        self,
        *,
        build_brief: BuildBrief,
        dry_run: bool = True,
    ) -> tuple[FactoryRunResult, FactoryTrackingResult]:
        """Trigger external workflow_dispatch and run local orchestrator tracking."""
        workflow_run_id = f"ghrun-{uuid.uuid4().hex[:12]}"
        dispatch_inputs = {
            "project_id": build_brief.project_id,
            "dry_run": dry_run,
            "brief_hash": build_brief.brief_hash(),
        }
        workflow_dispatched = self._github_client.dispatch_workflow(
            owner=self._factory_owner,
            repo=self._factory_repo,
            workflow_id=self._workflow_id,
            inputs=dispatch_inputs,
        )

        # Local orchestrator run remains the deterministic source of run output
        # while factory workflow output ingestion is not yet available.
        run = self._orchestrator.run_factory_build(build_brief, dry_run=dry_run)
        run.events.append(
            {
                "timestamp": _utcnow_iso(),
                "step": "workflow_dispatch",
                "status": "ok" if workflow_dispatched else "failed",
                "details": {
                    "factory_owner": self._factory_owner,
                    "factory_repo": self._factory_repo,
                    "workflow_id": self._workflow_id,
                    "workflow_run_id": workflow_run_id,
                    "inputs": dispatch_inputs,
                    "build_brief_payload": build_brief.model_dump(mode="json", by_alias=True),
                },
            },
        )
        run.events.append(
            {
                "timestamp": _utcnow_iso(),
                "step": "factory_response_parsed",
                "status": "ok",
                "details": {
                    "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                    "repo_url": run.repo_url,
                    "deployment_url": run.deploy_url,
                },
            },
        )
        run.updated_at = _utcnow_iso()
        self._orchestrator.store.upsert(run)

        tracking = FactoryTrackingResult(
            run_id=run.run_id,
            workflow_dispatched=workflow_dispatched,
            workflow_run_id=workflow_run_id,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            repo_url=run.repo_url,
            deployment_url=run.deploy_url,
        )
        return run, tracking

    def get_tracking(self, run_id: str) -> FactoryTrackingResult | None:
        """Read tracking information for an existing run."""
        run = self._orchestrator.get_run(run_id)
        if run is None:
            return None

        workflow_event = None
        for event in reversed(run.events):
            if event.get("step") == "workflow_dispatch":
                workflow_event = event
                break

        details = workflow_event.get("details", {}) if workflow_event else {}
        return FactoryTrackingResult(
            run_id=run.run_id,
            workflow_dispatched=bool(workflow_event and workflow_event.get("status") == "ok"),
            workflow_run_id=details.get("workflow_run_id"),
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            repo_url=run.repo_url,
            deployment_url=run.deploy_url,
        )
