"""Tests for the GitHub Factory orchestrator run flow."""

from __future__ import annotations

from app.factory.models import BuildBrief, FactoryRunStatus
from app.factory.orchestrator import FactoryOrchestrator, FactoryRunStore
from app.integrations.github_client import GitHubClient
from app.integrations.vercel_client import VercelClient


def _make_brief() -> BuildBrief:
    return BuildBrief(
        project_id="PRJ-002",
        idea_id="IDEA-002",
        hypothesis="Users will sign up if proposal writing is faster.",
        target_user="Freelancers writing proposals",
        problem="Proposal writing is repetitive and slow.",
        solution="Generate high-quality proposals from short prompts.",
        mvp_scope=[
            "Single landing page",
            "Email capture endpoint",
            "Basic analytics events",
        ],
        acceptance_criteria=[
            "Landing page deployed and reachable",
            "CTA collects emails",
            "Visits and signups are tracked",
        ],
        landing_page_requirements=[
            "Headline focused on outcome",
            "Primary CTA text: Get early access",
            "Simple social proof section",
        ],
        cta="Get early access",
        pricing_hint="Early access waitlist then $9/month beta",
        deployment_target="vercel",
        command_bundle={"framework": "nextjs"},
    )


def _make_orchestrator() -> FactoryOrchestrator:
    return FactoryOrchestrator(
        github_client=GitHubClient(token="test-token"),
        vercel_client=VercelClient(token="test-vercel-token"),
        run_store=FactoryRunStore(),
        github_owner="ai-dan",
        repo_template="saas-template",
    )


def test_dry_run_succeeds_with_preview_urls() -> None:
    orchestrator = _make_orchestrator()
    run = orchestrator.run_factory_build(_make_brief(), dry_run=True)

    assert run.status == FactoryRunStatus.SUCCEEDED
    assert run.repo_url is not None
    assert run.repo_url.startswith("dry-run://github/")
    assert run.deploy_url is not None
    assert run.deploy_url.startswith("dry-run://vercel/")
    assert run.error is None


def test_live_run_succeeds_with_stub_urls() -> None:
    orchestrator = _make_orchestrator()
    run = orchestrator.run_factory_build(_make_brief(), dry_run=False)

    assert run.status == FactoryRunStatus.SUCCEEDED
    assert run.repo_url is not None
    assert "github.com" in run.repo_url
    assert run.deploy_url is not None
    assert "vercel.app" in run.deploy_url
    assert run.stub is True


def test_idempotency_replays_existing_run() -> None:
    orchestrator = _make_orchestrator()
    first = orchestrator.run_factory_build(_make_brief(), dry_run=True)
    second = orchestrator.run_factory_build(_make_brief(), dry_run=True)

    assert second.run_id == first.run_id
    assert second.status == FactoryRunStatus.SUCCEEDED
    assert any(event["step"] == "idempotency_replay" for event in second.events)


def test_get_run_returns_saved_run() -> None:
    orchestrator = _make_orchestrator()
    run = orchestrator.run_factory_build(_make_brief(), dry_run=True)
    fetched = orchestrator.get_run(run.run_id)
    assert fetched is not None
    assert fetched.run_id == run.run_id


def test_invalid_repo_name_fails_cleanly() -> None:
    orchestrator = _make_orchestrator()
    brief = _make_brief().model_copy(update={"project_id": "!!!"})
    run = orchestrator.run_factory_build(brief, dry_run=False)

    assert run.status == FactoryRunStatus.FAILED
    assert run.error is not None
    assert "valid repository name" in run.error
