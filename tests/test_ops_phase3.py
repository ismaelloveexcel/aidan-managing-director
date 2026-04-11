"""Tests for Phase 3 operational endpoints: readiness, SLO, dead-letter queue."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestReadinessGate(unittest.TestCase):
    """Tests for GET /ops/ready."""

    def test_readiness_returns_200(self) -> None:
        resp = client.get("/ops/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert "ready" in body
        assert "checks" in body
        assert isinstance(body["checks"], list)

    def test_readiness_includes_expected_checks(self) -> None:
        resp = client.get("/ops/ready")
        body = resp.json()
        check_names = {c["name"] for c in body["checks"]}
        assert "secrets" in check_names
        assert "portfolio_db" in check_names
        assert "factory_run_store" in check_names
        assert "callback_secret" in check_names
        assert "public_base_url" in check_names


class TestSLODashboard(unittest.TestCase):
    """Tests for GET /ops/slo."""

    def test_slo_returns_200(self) -> None:
        resp = client.get("/ops/slo")
        assert resp.status_code == 200
        body = resp.json()
        assert "window_hours" in body
        assert "event_types" in body
        assert "stuck_jobs" in body
        assert "dead_letter_counts" in body

    def test_slo_custom_hours(self) -> None:
        resp = client.get("/ops/slo?hours=1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["window_hours"] == 1


class TestDeadLetterQueue(unittest.TestCase):
    """Tests for /ops/dlq endpoints."""

    def test_dlq_list_returns_200(self) -> None:
        resp = client.get("/ops/dlq")
        assert resp.status_code == 200
        body = resp.json()
        assert "entries" in body
        assert "total" in body

    def test_dlq_enqueued_on_orphan_callback(self) -> None:
        """A callback with no matching run should enqueue a DLQ entry."""
        from app.core.dependencies import get_dead_letter_queue

        dlq = get_dead_letter_queue()
        dlq.reset()

        # Send callback with a correlation_id that doesn't exist
        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-DLQ-TEST",
                "correlation_id": "PRJ-DLQ-TEST:orphan123456",
                "status": "failed",
                "error": "build failed",
            },
        )
        assert resp.status_code == 200

        # Verify it was enqueued
        entries = dlq.list_all(limit=10)
        found = [e for e in entries if e.correlation_id == "PRJ-DLQ-TEST:orphan123456"]
        assert len(found) == 1
        assert found[0].status == "pending"

    def test_dlq_resolve(self) -> None:
        """POST /ops/dlq/{dlq_id}/resolve marks entry as resolved."""
        from app.core.dependencies import get_dead_letter_queue
        from app.factory.dead_letter import DeadLetterEntry

        dlq = get_dead_letter_queue()
        dlq.reset()

        entry = DeadLetterEntry(
            correlation_id="test-corr-123",
            project_id="PRJ-RESOLVE",
            payload={"test": True},
            error="test error",
        )
        dlq.enqueue(entry)

        resp = client.post(f"/ops/dlq/{entry.dlq_id}/resolve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

        # Verify no more pending
        pending = dlq.list_pending(limit=10)
        assert len(pending) == 0


class TestOpsEventRecording(unittest.TestCase):
    """Tests for ops event tracking in callback flow."""

    def test_callback_records_ops_event(self) -> None:
        """Factory callback should record an ops event."""
        from app.core.dependencies import get_factory_run_store, get_ops_event_store

        ops = get_ops_event_store()
        ops.reset()
        store = get_factory_run_store()
        store.reset()

        from app.factory.models import FactoryRunResult, FactoryRunStatus

        # Need a project for the run
        from app.core.dependencies import get_portfolio_repository

        repo = get_portfolio_repository()
        try:
            repo.create_project(
                name="ops-test",
                description="test",
                project_id="PRJ-OPS-EVT",
            )
        except Exception:
            pass

        run = FactoryRunResult(
            project_id="PRJ-OPS-EVT",
            idea_id="IDEA-OPS-1",
            status=FactoryRunStatus.DISPATCHED,
            idempotency_key="PRJ-OPS-EVT:ops-key:dry_run",
            dry_run=True,
            correlation_id="PRJ-OPS-EVT:ops12345678",
        )
        store.upsert(run)

        client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-OPS-EVT",
                "correlation_id": "PRJ-OPS-EVT:ops12345678",
                "status": "succeeded",
                "deploy_url": "https://ops-test.vercel.app",
            },
        )

        # Verify ops event was recorded
        summary = ops.slo_summary(hours=1)
        assert "callback" in summary.get("event_types", {})
        cb_stats = summary["event_types"]["callback"]
        assert cb_stats["total"] >= 1
        assert cb_stats["successes"] >= 1


class TestCrossRepoContract(unittest.TestCase):
    """Contract tests verifying dispatch → callback → state update loop."""

    def test_dispatch_callback_state_update_contract(self) -> None:
        """Full loop: create run → callback → verify state update."""
        from app.core.dependencies import get_factory_run_store, get_portfolio_repository
        from app.factory.models import FactoryRunResult, FactoryRunStatus

        store = get_factory_run_store()
        store.reset()
        repo = get_portfolio_repository()

        try:
            repo.create_project(
                name="contract-test",
                description="contract test project",
                project_id="PRJ-CONTRACT-1",
            )
        except Exception:
            pass

        # 1. Simulate dispatch: create DISPATCHED run
        run = FactoryRunResult(
            project_id="PRJ-CONTRACT-1",
            idea_id="IDEA-CONTRACT-1",
            status=FactoryRunStatus.DISPATCHED,
            idempotency_key="PRJ-CONTRACT-1:contract-key:live",
            dry_run=False,
            correlation_id="PRJ-CONTRACT-1:contract12345",
        )
        store.upsert(run)
        repo.save_factory_run(run)

        # 2. Factory sends callback with succeeded status
        resp = client.post(
            "/factory/callback",
            json={
                "project_id": "PRJ-CONTRACT-1",
                "correlation_id": "PRJ-CONTRACT-1:contract12345",
                "run_id": run.run_id,
                "status": "deployed",
                "deploy_url": "https://contract-test.vercel.app",
                "repo_url": "https://github.com/test/contract-repo",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deployed"

        # 3. Verify state was updated in run store
        updated = store.get_by_correlation_id("PRJ-CONTRACT-1:contract12345")
        assert updated is not None
        assert updated.status == FactoryRunStatus.DEPLOYED
        assert updated.deploy_url == "https://contract-test.vercel.app"
        assert updated.repo_url == "https://github.com/test/contract-repo"

        # 4. Verify polling endpoint returns correct status
        poll_resp = client.get("/factory/runs/PRJ-CONTRACT-1:contract12345/result")
        assert poll_resp.status_code == 200
        assert poll_resp.json()["status"] == "deployed"
        assert poll_resp.json()["found"] is True
