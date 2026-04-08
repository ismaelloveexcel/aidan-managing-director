"""Tests for factory callback, correlation_id, polling, and Turso adapter."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.core.dependencies import get_factory_run_store, get_portfolio_repository
from app.factory.factory_client import generate_correlation_id
from app.factory.models import FactoryRunResult, FactoryRunStatus
from main import app

client = TestClient(app)


def _brief_payload() -> dict:
    return {
        "project_id": "PRJ-CB-1",
        "idea_id": "IDEA-CB-1",
        "hypothesis": "A focused landing page can capture demand quickly.",
        "target_user": "indie founders",
        "problem": "Idea validation is too slow and manual.",
        "solution": "Automatically generate and deploy single-purpose MVP pages.",
        "mvp_scope": ["Landing page", "CTA endpoint"],
        "acceptance_criteria": ["Page loads", "CTA submits successfully"],
        "landing_page_requirements": [
            "Primary CTA: Get early access",
            "Clear value proposition above the fold",
        ],
        "cta": "Get early access",
        "pricing_hint": "Free waitlist",
        "deployment_target": "vercel",
        "command_bundle": {"entrypoint": "factory.run"},
        "feature_flags": {"dry_run": True, "live_factory": False},
    }


# ---------------------------------------------------------------------------
# correlation_id generation
# ---------------------------------------------------------------------------


class TestCorrelationId:
    def test_format_includes_project_id(self) -> None:
        cid = generate_correlation_id("PRJ-123")
        assert cid.startswith("PRJ-123:")
        assert len(cid.split(":")) == 2

    def test_unique_per_call(self) -> None:
        ids = {generate_correlation_id("PRJ-X") for _ in range(50)}
        assert len(ids) == 50

    def test_hex_suffix_length(self) -> None:
        cid = generate_correlation_id("PRJ-A")
        suffix = cid.split(":")[1]
        assert len(suffix) == 12


# ---------------------------------------------------------------------------
# /factory/callback endpoint
# ---------------------------------------------------------------------------


class TestFactoryCallback:
    def _seed_run(self, correlation_id: str, project_id: str = "PRJ-CB-1") -> FactoryRunResult:
        store = get_factory_run_store()
        run = FactoryRunResult(
            project_id=project_id,
            idea_id="IDEA-CB-1",
            status=FactoryRunStatus.RUNNING,
            idempotency_key=f"{project_id}:test-key:dry_run",
            dry_run=True,
            correlation_id=correlation_id,
        )
        store.upsert(run)
        return run

    def test_callback_success(self) -> None:
        store = get_factory_run_store()
        store.reset()
        run = self._seed_run("PRJ-CB-1:abc123def456")

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": run.project_id,
                "correlation_id": "PRJ-CB-1:abc123def456",
                "status": "succeeded",
                "deploy_url": "https://example.vercel.app",
                "repo_url": "https://github.com/test/repo",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["received"] is True
        assert body["correlation_id"] == "PRJ-CB-1:abc123def456"
        assert body["status"] == "succeeded"

        # Verify in-memory store was updated
        updated = store.get_by_correlation_id("PRJ-CB-1:abc123def456")
        assert updated is not None
        assert updated.status == FactoryRunStatus.SUCCEEDED
        assert updated.deploy_url == "https://example.vercel.app"

    def test_callback_failure(self) -> None:
        store = get_factory_run_store()
        store.reset()
        self._seed_run("PRJ-CB-1:fail123fail45")

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-CB-1",
                "correlation_id": "PRJ-CB-1:fail123fail45",
                "status": "failed",
                "error": "Build timed out",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"

        updated = store.get_by_correlation_id("PRJ-CB-1:fail123fail45")
        assert updated is not None
        assert updated.status == FactoryRunStatus.FAILED

    def test_callback_deployed_status(self) -> None:
        store = get_factory_run_store()
        store.reset()
        self._seed_run("PRJ-CB-1:deploy123456")

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-CB-1",
                "correlation_id": "PRJ-CB-1:deploy123456",
                "status": "deployed",
                "deploy_url": "https://deployed.vercel.app",
            },
        )
        assert resp.status_code == 200
        updated = store.get_by_correlation_id("PRJ-CB-1:deploy123456")
        assert updated is not None
        assert updated.status == FactoryRunStatus.DEPLOYED

    def test_callback_building_status(self) -> None:
        store = get_factory_run_store()
        store.reset()
        self._seed_run("PRJ-CB-1:build1234567")

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-CB-1",
                "correlation_id": "PRJ-CB-1:build1234567",
                "status": "building",
            },
        )
        assert resp.status_code == 200
        updated = store.get_by_correlation_id("PRJ-CB-1:build1234567")
        assert updated is not None
        assert updated.status == FactoryRunStatus.BUILDING

    def test_callback_idempotent(self) -> None:
        """Repeated callback with same data does not cause errors."""
        store = get_factory_run_store()
        store.reset()
        self._seed_run("PRJ-CB-1:idem12345678")

        payload = {
            "project_id": "PRJ-CB-1",
            "correlation_id": "PRJ-CB-1:idem12345678",
            "status": "succeeded",
            "deploy_url": "https://idem.vercel.app",
        }
        resp1 = client.post("/factory/callback", json=payload)
        resp2 = client.post("/factory/callback", json=payload)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["status"] == resp2.json()["status"]

    def test_callback_unknown_correlation_id(self) -> None:
        """Callback for unknown correlation_id still returns 200."""
        store = get_factory_run_store()
        store.reset()
        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-UNKNOWN",
                "correlation_id": "PRJ-UNKNOWN:notfound1234",
                "status": "failed",
                "error": "Unknown run",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["received"] is True


# ---------------------------------------------------------------------------
# /factory/runs/{correlation_id}/result polling endpoint
# ---------------------------------------------------------------------------


class TestPollingFallback:
    def test_poll_found(self) -> None:
        store = get_factory_run_store()
        store.reset()
        run = FactoryRunResult(
            project_id="PRJ-POLL-1",
            idea_id="IDEA-POLL-1",
            status=FactoryRunStatus.SUCCEEDED,
            idempotency_key="PRJ-POLL-1:poll-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-POLL-1:poll123poll1",
            repo_url="https://github.com/test/poll-repo",
            deploy_url="https://poll.vercel.app",
        )
        store.upsert(run)

        resp = client.get("/factory/runs/PRJ-POLL-1:poll123poll1/result")
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] is True
        assert body["correlation_id"] == "PRJ-POLL-1:poll123poll1"
        assert body["status"] == "succeeded"
        assert body["repo_url"] == "https://github.com/test/poll-repo"
        assert body["deploy_url"] == "https://poll.vercel.app"

    def test_poll_not_found(self) -> None:
        store = get_factory_run_store()
        store.reset()

        resp = client.get("/factory/runs/PRJ-MISSING:no12345no678/result")
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] is False
        assert body["correlation_id"] == "PRJ-MISSING:no12345no678"


# ---------------------------------------------------------------------------
# correlation_id in run creation flow
# ---------------------------------------------------------------------------


class TestCorrelationIdInFlow:
    def test_create_run_has_correlation_id(self) -> None:
        get_factory_run_store().reset()
        resp = client.post(
            "/factory/runs",
            json={"build_brief": _brief_payload(), "dry_run": True},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["correlation_id"] is not None
        assert body["correlation_id"].startswith("PRJ-CB-1:")

    def test_tracking_includes_correlation_id(self) -> None:
        get_factory_run_store().reset()
        created = client.post(
            "/factory/runs",
            json={"build_brief": _brief_payload(), "dry_run": True},
        )
        assert created.status_code == 200
        run_id = created.json()["run_id"]

        tracking = client.get(f"/factory/runs/{run_id}/tracking")
        assert tracking.status_code == 200
        body = tracking.json()
        assert body["correlation_id"] is not None
        assert body["correlation_id"].startswith("PRJ-CB-1:")


# ---------------------------------------------------------------------------
# FactoryRunStore correlation_id lookup
# ---------------------------------------------------------------------------


class TestRunStoreCorrelationLookup:
    def test_get_by_correlation_id(self) -> None:
        store = get_factory_run_store()
        store.reset()
        run = FactoryRunResult(
            project_id="PRJ-STORE-1",
            idea_id="IDEA-STORE-1",
            status=FactoryRunStatus.RUNNING,
            idempotency_key="PRJ-STORE-1:store-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-STORE-1:store1234567",
        )
        store.upsert(run)

        found = store.get_by_correlation_id("PRJ-STORE-1:store1234567")
        assert found is not None
        assert found.run_id == run.run_id

    def test_get_by_correlation_id_not_found(self) -> None:
        store = get_factory_run_store()
        store.reset()
        assert store.get_by_correlation_id("nonexistent") is None


# ---------------------------------------------------------------------------
# Turso adapter (unit-level)
# ---------------------------------------------------------------------------


class TestTursoAdapter:
    def test_fallback_to_sqlite_when_no_turso_creds(self) -> None:
        from app.portfolio.db_adapter import TursoPortfolioDB

        db = TursoPortfolioDB(
            db_path=":memory:",
            turso_database_url="",
            turso_auth_token="",
        )
        assert db._use_turso is False
        conn = db.connect()
        assert conn is not None
        conn.close()

    def test_schema_init_with_adapter(self, tmp_path: Any) -> None:
        from pathlib import Path

        from app.portfolio.db_adapter import TursoPortfolioDB

        db_file = str(Path(str(tmp_path)) / "test_adapter.db")
        db = TursoPortfolioDB(
            db_path=db_file,
            turso_database_url="",
            turso_auth_token="",
        )
        db.init_schema()
        # Verify the schema was created
        with db.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {row["name"] for row in tables}
            assert "projects" in table_names
            assert "factory_runs" in table_names
            assert "build_briefs" in table_names

    def test_correlation_id_column_exists_after_init(self, tmp_path: Any) -> None:
        from pathlib import Path

        from app.portfolio.db_adapter import TursoPortfolioDB

        db_file = str(Path(str(tmp_path)) / "test_corr_col.db")
        db = TursoPortfolioDB(
            db_path=db_file,
            turso_database_url="",
            turso_auth_token="",
        )
        db.init_schema()
        with db.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(factory_runs)").fetchall()
            }
            assert "correlation_id" in columns


# ---------------------------------------------------------------------------
# Portfolio repository correlation_id persistence
# ---------------------------------------------------------------------------


class TestPortfolioCorrelationPersistence:
    def test_save_and_fetch_by_correlation_id(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        repo.create_project(
            name="test-corr",
            description="test",
            project_id="PRJ-CORR-1",
        )

        run = FactoryRunResult(
            project_id="PRJ-CORR-1",
            idea_id="IDEA-CORR-1",
            status=FactoryRunStatus.RUNNING,
            idempotency_key="PRJ-CORR-1:corr-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-CORR-1:corr12345678",
        )
        saved = repo.save_factory_run(run)
        assert saved.correlation_id == "PRJ-CORR-1:corr12345678"

        fetched = repo.get_factory_run_by_correlation_id("PRJ-CORR-1:corr12345678")
        assert fetched is not None
        assert fetched.run_id == run.run_id
        assert fetched.correlation_id == "PRJ-CORR-1:corr12345678"

    def test_fetch_nonexistent_correlation_id(self) -> None:
        repo = get_portfolio_repository()
        repo.reset()
        assert repo.get_factory_run_by_correlation_id("nonexistent") is None


# ---------------------------------------------------------------------------
# FactoryRunStatus new enum members
# ---------------------------------------------------------------------------


class TestFactoryRunStatusEnum:
    def test_dispatched_status(self) -> None:
        assert FactoryRunStatus.DISPATCHED.value == "dispatched"

    def test_building_status(self) -> None:
        assert FactoryRunStatus.BUILDING.value == "building"

    def test_deployed_status(self) -> None:
        assert FactoryRunStatus.DEPLOYED.value == "deployed"

    def test_all_statuses_present(self) -> None:
        values = {s.value for s in FactoryRunStatus}
        assert values == {
            "pending", "dispatched", "building", "running",
            "deployed", "succeeded", "failed",
        }


# ---------------------------------------------------------------------------
# Callback authentication tests
# ---------------------------------------------------------------------------


class TestCallbackAuthentication:
    """Test X-Factory-Secret header authentication on /factory/callback."""

    def test_callback_rejected_with_wrong_secret(self, monkeypatch: Any) -> None:
        """When factory_callback_secret is set, wrong header → 401."""
        from app.core.config import get_settings
        from app.routes import factory as factory_mod

        original_settings = get_settings()
        patched = original_settings.model_copy(update={"factory_callback_secret": "correct-secret"})
        monkeypatch.setattr(factory_mod, "get_settings", lambda: patched)

        store = get_factory_run_store()
        store.reset()

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-AUTH-1",
                "correlation_id": "PRJ-AUTH-1:auth12345678",
                "status": "succeeded",
            },
            headers={"X-Factory-Secret": "wrong-secret"},
        )
        assert resp.status_code == 401

    def test_callback_rejected_with_missing_secret(self, monkeypatch: Any) -> None:
        """When factory_callback_secret is set, missing header → 401."""
        from app.core.config import get_settings
        from app.routes import factory as factory_mod

        original_settings = get_settings()
        patched = original_settings.model_copy(update={"factory_callback_secret": "correct-secret"})
        monkeypatch.setattr(factory_mod, "get_settings", lambda: patched)

        store = get_factory_run_store()
        store.reset()

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-AUTH-2",
                "correlation_id": "PRJ-AUTH-2:auth12345678",
                "status": "succeeded",
            },
        )
        assert resp.status_code == 401

    def test_callback_accepted_with_correct_secret(self, monkeypatch: Any) -> None:
        """When factory_callback_secret is set, correct header → 200."""
        from app.core.config import get_settings
        from app.routes import factory as factory_mod

        original_settings = get_settings()
        patched = original_settings.model_copy(update={"factory_callback_secret": "correct-secret"})
        monkeypatch.setattr(factory_mod, "get_settings", lambda: patched)

        store = get_factory_run_store()
        store.reset()

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-AUTH-3",
                "correlation_id": "PRJ-AUTH-3:auth12345678",
                "status": "succeeded",
            },
            headers={"X-Factory-Secret": "correct-secret"},
        )
        assert resp.status_code == 200
        assert resp.json()["received"] is True

    def test_callback_accepted_when_no_secret_configured(self) -> None:
        """When factory_callback_secret is empty (dev mode), any request → 200."""
        store = get_factory_run_store()
        store.reset()

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-AUTH-4",
                "correlation_id": "PRJ-AUTH-4:auth12345678",
                "status": "failed",
            },
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Cold-start fallback: polling from portfolio DB
# ---------------------------------------------------------------------------


class TestPollingDbFallback:
    """Polling endpoint falls back to portfolio DB when in-memory store is empty."""

    def test_poll_finds_run_in_portfolio_db_after_cold_start(self) -> None:
        """Run persisted in portfolio DB is returned even if in-memory store is empty."""
        store = get_factory_run_store()
        store.reset()
        repo = get_portfolio_repository()
        repo.reset()

        # Create project and save a factory run directly to the portfolio DB.
        repo.create_project(
            name="poll-db-test",
            description="test",
            project_id="PRJ-POLLDB-1",
        )
        run = FactoryRunResult(
            project_id="PRJ-POLLDB-1",
            idea_id="IDEA-POLLDB-1",
            status=FactoryRunStatus.SUCCEEDED,
            idempotency_key="PRJ-POLLDB-1:polldb-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-POLLDB-1:polldb123456",
            repo_url="https://github.com/test/poll-db-repo",
            deploy_url="https://poll-db.vercel.app",
        )
        repo.save_factory_run(run)

        # Clear in-memory store to simulate cold start.
        store.reset()

        resp = client.get("/factory/runs/PRJ-POLLDB-1:polldb123456/result")
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] is True
        assert body["correlation_id"] == "PRJ-POLLDB-1:polldb123456"
        assert body["status"] == "succeeded"
        assert body["repo_url"] == "https://github.com/test/poll-db-repo"
        assert body["deploy_url"] == "https://poll-db.vercel.app"

    def test_poll_rehydrates_in_memory_store(self) -> None:
        """After DB fallback, the run is rehydrated into the in-memory store."""
        store = get_factory_run_store()
        store.reset()
        repo = get_portfolio_repository()
        repo.reset()

        repo.create_project(
            name="rehydrate-test",
            description="test",
            project_id="PRJ-REHY-1",
        )
        run = FactoryRunResult(
            project_id="PRJ-REHY-1",
            idea_id="IDEA-REHY-1",
            status=FactoryRunStatus.DEPLOYED,
            idempotency_key="PRJ-REHY-1:rehy-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-REHY-1:rehy12345678",
        )
        repo.save_factory_run(run)
        store.reset()

        # First poll triggers DB fallback + rehydration.
        client.get("/factory/runs/PRJ-REHY-1:rehy12345678/result")

        # After rehydration, the in-memory store should have the run.
        rehydrated = store.get_by_correlation_id("PRJ-REHY-1:rehy12345678")
        assert rehydrated is not None
        assert rehydrated.run_id == run.run_id


# ---------------------------------------------------------------------------
# Cold-start fallback: callback from portfolio DB
# ---------------------------------------------------------------------------


class TestCallbackDbFallback:
    """Callback endpoint falls back to portfolio DB when in-memory store is empty."""

    def test_callback_rehydrates_from_portfolio_db(self) -> None:
        """Callback for a run in portfolio DB but not in-memory store succeeds."""
        store = get_factory_run_store()
        store.reset()
        repo = get_portfolio_repository()
        repo.reset()

        repo.create_project(
            name="cb-db-test",
            description="test",
            project_id="PRJ-CBDB-1",
        )
        run = FactoryRunResult(
            project_id="PRJ-CBDB-1",
            idea_id="IDEA-CBDB-1",
            status=FactoryRunStatus.RUNNING,
            idempotency_key="PRJ-CBDB-1:cbdb-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-CBDB-1:cbdb12345678",
        )
        repo.save_factory_run(run)

        # Clear in-memory store to simulate cold start.
        store.reset()

        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-CBDB-1",
                "correlation_id": "PRJ-CBDB-1:cbdb12345678",
                "status": "succeeded",
                "deploy_url": "https://cbdb.vercel.app",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "succeeded"

        # Verify in-memory store was rehydrated with updated status.
        updated = store.get_by_correlation_id("PRJ-CBDB-1:cbdb12345678")
        assert updated is not None
        assert updated.status == FactoryRunStatus.SUCCEEDED
        assert updated.deploy_url == "https://cbdb.vercel.app"
