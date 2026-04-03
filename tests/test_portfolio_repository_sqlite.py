"""Tests for SQLite-backed portfolio repository behavior."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_portfolio_repository
from app.factory.models import BuildBrief, FactoryRunResult, FactoryRunStatus
from app.portfolio.models import LifecycleState
from app.portfolio.repository import PortfolioRepository
from app.portfolio.state_machine import InvalidStateTransitionError
from main import app

client = TestClient(app)


def _make_repo(tmp_path) -> PortfolioRepository:
    db_path = tmp_path / "portfolio.sqlite3"
    return PortfolioRepository(db_path=str(db_path))


def _make_brief(project_id: str) -> BuildBrief:
    return BuildBrief(
        project_id=project_id,
        idea_id="IDEA-PH2-1",
        hypothesis="Users will submit when value proposition is explicit.",
        target_user="Indie founders",
        problem="Validation cycles are too slow.",
        solution="Automated build and deploy loop with clear CTA.",
        mvp_scope=["Landing page", "CTA endpoint"],
        acceptance_criteria=["Page is live", "CTA works"],
        landing_page_requirements=["Primary CTA: Get early access"],
        cta="Get early access",
        pricing_hint="Free waitlist",
        deployment_target="vercel",
        command_bundle={"entrypoint": "factory.run"},
        validation_score=0.9,
        risk_flags=["scope_risk_medium"],
        monetization_model="waitlist",
        deployment_plan={"target": "vercel"},
        launch_gate={"requires_cta": True},
    )


def test_create_project_persists_and_logs_idea_created(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    project = repo.create_project(name="alpha", description="phase2 test")

    assert project.status == LifecycleState.IDEA
    events = repo.list_events(project.project_id)
    assert any(event.event_type == "idea_created" for event in events)


def test_transition_enforces_lifecycle_rules(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    project = repo.create_project(name="alpha", description="phase2 test")

    review = repo.transition_project_state(
        project_id=project.project_id,
        new_state=LifecycleState.REVIEW,
    )
    assert review is not None
    assert review.status == LifecycleState.REVIEW

    with pytest.raises(InvalidStateTransitionError):
        repo.transition_project_state(
            project_id=project.project_id,
            new_state=LifecycleState.LAUNCHED,
        )


def test_save_build_brief_and_load_latest(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    project = repo.create_project(name="alpha", description="phase2 test")
    brief = _make_brief(project.project_id)

    saved = repo.save_build_brief(project_id=project.project_id, brief=brief)
    latest = repo.get_latest_build_brief(project.project_id)

    assert latest is not None
    assert saved.brief_hash == brief.brief_hash()
    assert latest.idempotency_key == brief.idempotency_key()
    assert "validated" in [event.event_type for event in repo.list_events(project.project_id)]


def test_save_metrics_snapshot_normalizes_conversion(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    project = repo.create_project(name="alpha", description="phase2 test")

    snapshot = repo.save_metrics_snapshot(
        project_id=project.project_id,
        visits=250,
        signups=5,
        revenue=0.0,
        currency="USD",
        timestamp="2026-04-03T12:00:00+00:00",
        raw_payload={"source": "test"},
    )

    assert snapshot.conversion_rate == 5 / 250
    latest = repo.get_latest_metrics_snapshot(project.project_id)
    assert latest is not None
    assert latest.snapshot_id == snapshot.snapshot_id


def test_save_factory_run_and_lookup_by_idempotency_key(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    project = repo.create_project(name="alpha", description="phase2 test")
    brief = _make_brief(project.project_id)
    run = FactoryRunResult(
        project_id=project.project_id,
        idea_id=brief.idea_id,
        status=FactoryRunStatus.SUCCEEDED,
        idempotency_key=brief.idempotency_key(),
        dry_run=True,
        repo_url="dry-run://github/ai-dan/prj-x",
        deploy_url="dry-run://vercel/prj-x",
    )

    saved = repo.save_factory_run(run)
    loaded = repo.get_factory_run_by_idempotency_key(brief.idempotency_key())

    assert saved.run_id == run.run_id
    assert loaded is not None
    assert loaded.run_id == run.run_id
    assert "deployed" in [event.event_type for event in repo.list_events(project.project_id)]


def test_idempotency_keys_unique_constraint(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    key = "prj-unique:hash"

    with repo._db.connect() as conn:  # noqa: SLF001 - intentional direct DB assertion
        conn.execute(
            """
            INSERT INTO idempotency_keys (idempotency_key, run_id, project_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, "run-1", "prj-a", "2026-04-03T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO idempotency_keys (idempotency_key, run_id, project_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, "run-2", "prj-b", "2026-04-03T00:00:01+00:00"),
            )


def test_portfolio_route_returns_409_for_invalid_transition() -> None:
    repo = get_portfolio_repository()
    repo.reset()

    create_resp = client.post(
        "/portfolio/projects",
        json={"name": "route-check", "description": "route validation"},
    )
    assert create_resp.status_code == 200
    project_id = create_resp.json()["project_id"]

    transition_resp = client.post(
        f"/portfolio/projects/{project_id}/transition",
        json={"new_state": "launched"},
    )
    assert transition_resp.status_code == 409
