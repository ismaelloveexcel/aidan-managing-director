"""
SQLite-backed repository for portfolio state, events, and metrics.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.factory.models import BuildBrief, FactoryRunResult
from app.portfolio.db import PortfolioDB
from app.portfolio.db_adapter import TursoPortfolioDB
from app.portfolio.models import (
    BuildBriefRecord,
    FactoryRunRecord,
    LifecycleState,
    MetricsSnapshotRecord,
    PortfolioEventRecord,
    PortfolioProjectRecord,
    utcnow_iso,
)
from app.portfolio.state_machine import assert_transition_allowed


class PortfolioRepository:
    """Persistence gateway for controlled project lifecycle operations."""

    def __init__(
        self,
        db_path: str = "data/portfolio.sqlite3",
        db: PortfolioDB | TursoPortfolioDB | None = None,
        turso_database_url: str = "",
        turso_auth_token: str = "",
    ) -> None:
        if db is not None:
            self._db = db
        elif turso_database_url and turso_auth_token:
            self._db = TursoPortfolioDB(
                db_path=db_path,
                turso_database_url=turso_database_url,
                turso_auth_token=turso_auth_token,
            )
        else:
            self._db = PortfolioDB(db_path=db_path)
        self._db.init_schema()

    # ------------------------------------------------------------------
    # Project records
    # ------------------------------------------------------------------

    def create_project(
        self,
        *,
        name: str,
        description: str,
        metadata: dict[str, Any] | None = None,
        status: LifecycleState = LifecycleState.IDEA,
        project_id: str | None = None,
    ) -> PortfolioProjectRecord:
        """Create a project and emit the mandatory `idea_created` audit event."""
        resolved_project_id = project_id or f"prj-{uuid.uuid4().hex[:8]}"
        now = utcnow_iso()
        metadata_json = json.dumps(metadata or {}, sort_keys=True)

        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, description, status, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_project_id,
                    name,
                    description,
                    status.value,
                    metadata_json,
                    now,
                    now,
                ),
            )

        self.log_event(
            project_id=resolved_project_id,
            event_type="idea_created",
            payload={"name": name, "status": status.value},
        )
        project = self.get_project(resolved_project_id)
        assert project is not None
        return project

    def get_project(self, project_id: str) -> PortfolioProjectRecord | None:
        """Fetch a single project by ID."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT project_id, name, description, status, metadata_json, created_at, updated_at
                FROM projects
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
        return self._to_project_record(row) if row is not None else None

    def list_projects(self) -> list[PortfolioProjectRecord]:
        """Return all projects ordered by creation timestamp."""
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT project_id, name, description, status, metadata_json, created_at, updated_at
                FROM projects
                ORDER BY created_at ASC
                """,
            ).fetchall()
        return [self._to_project_record(row) for row in rows]

    def update_project_metadata(
        self,
        *,
        project_id: str,
        metadata_updates: dict[str, Any],
    ) -> PortfolioProjectRecord | None:
        """Merge metadata updates into a project's stored metadata JSON."""
        project = self.get_project(project_id)
        if project is None:
            return None
        merged = dict(project.metadata)
        merged.update(metadata_updates)
        now = utcnow_iso()
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET metadata_json = ?, updated_at = ?
                WHERE project_id = ?
                """,
                (json.dumps(merged, sort_keys=True), now, project_id),
            )
        return self.get_project(project_id)

    def transition_project_state(
        self,
        *,
        project_id: str,
        new_state: LifecycleState | str,
        event_type: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> PortfolioProjectRecord | None:
        """Transition project state with strict state-machine enforcement."""
        project = self.get_project(project_id)
        if project is None:
            return None

        target_state = LifecycleState(new_state)
        assert_transition_allowed(project.status, target_state)
        now = utcnow_iso()

        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET status = ?, updated_at = ?
                WHERE project_id = ?
                """,
                (target_state.value, now, project_id),
            )

        resolved_event_type = event_type or self._default_transition_event(target_state)
        self.log_event(
            project_id=project_id,
            event_type=resolved_event_type,
            payload={
                "from_state": project.status.value,
                "to_state": target_state.value,
                **(payload or {}),
            },
        )
        updated = self.get_project(project_id)
        assert updated is not None
        return updated

    # ------------------------------------------------------------------
    # BuildBrief persistence
    # ------------------------------------------------------------------

    def save_build_brief(self, *, project_id: str, brief: BuildBrief) -> BuildBriefRecord:
        """Persist a BuildBrief contract snapshot."""
        brief_id = f"brief-{uuid.uuid4().hex[:8]}"
        now = utcnow_iso()
        payload = brief.model_dump(mode="json", by_alias=True)

        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO build_briefs (
                    brief_id,
                    project_id,
                    schema_version,
                    brief_hash,
                    idempotency_key,
                    payload_json,
                    validation_score,
                    risk_flags_json,
                    monetization_model,
                    deployment_plan_json,
                    launch_gate_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brief_id,
                    project_id,
                    brief.schema_version,
                    brief.brief_hash(),
                    brief.idempotency_key(),
                    json.dumps(payload, sort_keys=True),
                    brief.validation_score,
                    json.dumps(brief.risk_flags, sort_keys=True),
                    brief.monetization_model,
                    json.dumps(brief.deployment_plan, sort_keys=True),
                    json.dumps(brief.launch_gate, sort_keys=True),
                    now,
                ),
            )
            inserted = cursor.rowcount > 0

        result = self.get_latest_build_brief(project_id)
        assert result is not None

        if inserted:
            self.log_event(
                project_id=project_id,
                event_type="validated",
                payload={
                    "brief_id": brief_id,
                    "brief_hash": brief.brief_hash(),
                    "idempotency_key": brief.idempotency_key(),
                },
            )
        return result

    def get_latest_build_brief(self, project_id: str) -> BuildBriefRecord | None:
        """Return most recently persisted BuildBrief for a project."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    brief_id,
                    project_id,
                    schema_version,
                    brief_hash,
                    idempotency_key,
                    payload_json,
                    validation_score,
                    risk_flags_json,
                    monetization_model,
                    deployment_plan_json,
                    launch_gate_json,
                    created_at
                FROM build_briefs
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return BuildBriefRecord(
            brief_id=row["brief_id"],
            project_id=row["project_id"],
            schema_version=row["schema_version"],
            brief_hash=row["brief_hash"],
            idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload_json"]),
            validation_score=float(row["validation_score"]),
            risk_flags=json.loads(row["risk_flags_json"]),
            monetization_model=row["monetization_model"],
            deployment_plan=json.loads(row["deployment_plan_json"]),
            launch_gate=json.loads(row["launch_gate_json"]),
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Factory run persistence and idempotency
    # ------------------------------------------------------------------

    def save_factory_run(self, run: FactoryRunResult) -> FactoryRunRecord:
        """Persist factory run output and idempotency mapping."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO factory_runs (
                    run_id, project_id, idea_id, status, idempotency_key, dry_run,
                    correlation_id, repo_url, deploy_url, error, events_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.project_id,
                    run.idea_id,
                    run.status.value if hasattr(run.status, "value") else str(run.status),
                    run.idempotency_key,
                    1 if run.dry_run else 0,
                    run.correlation_id,
                    run.repo_url,
                    run.deploy_url,
                    run.error,
                    json.dumps(run.events, sort_keys=True),
                    run.created_at,
                    run.updated_at,
                ),
            )
            existing_mapping = conn.execute(
                    """
                    SELECT run_id
                    FROM idempotency_keys
                    WHERE idempotency_key = ?
                    """,
                    (run.idempotency_key,),
                ).fetchone()
            if existing_mapping is None:
                conn.execute(
                    """
                    INSERT INTO idempotency_keys (
                        idempotency_key, run_id, project_id, created_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (run.idempotency_key, run.run_id, run.project_id, utcnow_iso()),
                )
            elif existing_mapping["run_id"] != run.run_id:
                raise ValueError(
                    "Idempotency key is already associated with a different run_id."
                )

            project_row = conn.execute(
                """
                SELECT metadata_json
                FROM projects
                WHERE project_id = ?
                """,
                (run.project_id,),
            ).fetchone()
            if project_row is not None:
                metadata = json.loads(project_row["metadata_json"])
                metadata["build_status"] = (
                    run.status.value if hasattr(run.status, "value") else str(run.status)
                )
                if run.repo_url:
                    metadata["repo_url"] = run.repo_url
                if run.deploy_url:
                    metadata["deployment_url"] = run.deploy_url
                conn.execute(
                    """
                    UPDATE projects
                    SET metadata_json = ?, updated_at = ?
                    WHERE project_id = ?
                    """,
                    (json.dumps(metadata, sort_keys=True), utcnow_iso(), run.project_id),
                )

        run_status = run.status.value if hasattr(run.status, "value") else str(run.status)
        if run_status in ("running", "dispatched", "building"):
            event_type = "build_started"
        elif run_status in ("succeeded", "deployed"):
            event_type = "deployed"
        else:
            event_type = "build_failed"
        self.log_event(
            project_id=run.project_id,
            event_type=event_type,
            payload={"run_id": run.run_id, "status": run_status},
        )
        saved = self.get_factory_run(run.run_id)
        assert saved is not None
        return saved

    def list_factory_runs(self, limit: int = 25) -> list[FactoryRunRecord]:
        """Return recent factory runs in reverse-chronological order."""
        safe_limit = max(1, min(limit, 500))
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    run_id, project_id, idea_id, status, idempotency_key, dry_run,
                    correlation_id, repo_url, deploy_url, error, events_json,
                    created_at, updated_at
                FROM factory_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._to_factory_run_record(row) for row in rows]

    def get_factory_run(self, run_id: str) -> FactoryRunRecord | None:
        """Fetch a saved factory run by ID."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    run_id, project_id, idea_id, status, idempotency_key, dry_run,
                    correlation_id, repo_url, deploy_url, error, events_json,
                    created_at, updated_at
                FROM factory_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._to_factory_run_record(row) if row is not None else None

    def get_factory_run_by_idempotency_key(self, key: str) -> FactoryRunRecord | None:
        """Fetch a run using the persisted idempotency key mapping."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT fr.*
                FROM factory_runs fr
                INNER JOIN idempotency_keys ik ON ik.run_id = fr.run_id
                WHERE ik.idempotency_key = ?
                """,
                (key,),
            ).fetchone()
        return self._to_factory_run_record(row) if row is not None else None

    def get_factory_run_by_correlation_id(self, correlation_id: str) -> FactoryRunRecord | None:
        """Fetch a run by its correlation ID (used for callback/polling lookup)."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    run_id, project_id, idea_id, status, idempotency_key, dry_run,
                    correlation_id, repo_url, deploy_url, error, events_json,
                    created_at, updated_at
                FROM factory_runs
                WHERE correlation_id = ?
                """,
                (correlation_id,),
            ).fetchone()
        return self._to_factory_run_record(row) if row is not None else None

    def count_projects_by_state(self, states: set[LifecycleState] | set[str]) -> int:
        """Return number of projects in any of the provided lifecycle states."""
        resolved = [
            state.value if isinstance(state, LifecycleState) else str(state)
            for state in states
        ]
        if not resolved:
            return 0
        placeholders = ", ".join("?" for _ in resolved)
        with self._db.connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM projects
                WHERE status IN ({placeholders})
                """,
                tuple(resolved),
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    def count_factory_runs_by_status(
        self,
        statuses: set[str],
    ) -> int:
        """Return number of persisted factory runs matching given statuses."""
        resolved = [str(status) for status in statuses]
        if not resolved:
            return 0
        placeholders = ", ".join("?" for _ in resolved)
        with self._db.connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM factory_runs
                WHERE status IN ({placeholders})
                """,
                tuple(resolved),
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    def count_events_since(self, *, event_type: str, since_iso: str) -> int:
        """Return count of project events by type at/after the given timestamp."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM project_events
                WHERE event_type = ?
                  AND created_at >= ?
                """,
                (event_type, since_iso),
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    # ------------------------------------------------------------------
    # Metrics and decisions
    # ------------------------------------------------------------------

    def save_metrics_snapshot(
        self,
        *,
        project_id: str,
        visits: int,
        signups: int,
        revenue: float,
        currency: str,
        timestamp: str,
        raw_payload: dict[str, Any] | None = None,
    ) -> MetricsSnapshotRecord:
        """Persist a metrics snapshot and emit `metrics_updated` audit event."""
        snapshot_id = f"met-{uuid.uuid4().hex[:8]}"
        now = utcnow_iso()
        conversion_rate = float(signups) / float(max(visits, 1))
        raw_json = json.dumps(raw_payload or {}, sort_keys=True)

        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO metrics_snapshots (
                    snapshot_id, project_id, visits, signups, revenue, currency,
                    conversion_rate, timestamp, raw_payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    project_id,
                    visits,
                    signups,
                    revenue,
                    currency,
                    conversion_rate,
                    timestamp,
                    raw_json,
                    now,
                ),
            )

        self.log_event(
            project_id=project_id,
            event_type="metrics_updated",
            payload={
                "snapshot_id": snapshot_id,
                "visits": visits,
                "signups": signups,
                "revenue": revenue,
                "conversion_rate": conversion_rate,
            },
        )
        metrics = self.get_latest_metrics_snapshot(project_id)
        assert metrics is not None
        return metrics

    def get_latest_metrics_snapshot(self, project_id: str) -> MetricsSnapshotRecord | None:
        """Return latest metrics snapshot by business timestamp."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    snapshot_id, project_id, visits, signups, revenue, currency,
                    conversion_rate, timestamp, raw_payload_json, created_at
                FROM metrics_snapshots
                WHERE project_id = ?
                ORDER BY timestamp DESC, created_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return MetricsSnapshotRecord(
            snapshot_id=row["snapshot_id"],
            project_id=row["project_id"],
            visits=int(row["visits"]),
            signups=int(row["signups"]),
            revenue=float(row["revenue"]),
            currency=row["currency"],
            conversion_rate=float(row["conversion_rate"]),
            timestamp=row["timestamp"],
            raw_payload=json.loads(row["raw_payload_json"]),
            created_at=row["created_at"],
        )

    def record_decision_applied(self, *, project_id: str, decision: dict[str, Any]) -> None:
        """Persist a decision audit event without auto-transitioning state."""
        self.log_event(
            project_id=project_id,
            event_type="decision_applied",
            payload=decision,
        )

    # ------------------------------------------------------------------
    # Audit events
    # ------------------------------------------------------------------

    def log_event(
        self,
        *,
        project_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> PortfolioEventRecord:
        """Persist an audit event and return the inserted record."""
        event_id = f"evt-{uuid.uuid4().hex[:10]}"
        now = utcnow_iso()
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO project_events (event_id, project_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, project_id, event_type, json.dumps(payload or {}, sort_keys=True), now),
            )
        return PortfolioEventRecord(
            event_id=event_id,
            project_id=project_id,
            event_type=event_type,
            payload=payload or {},
            created_at=now,
        )

    def list_events(self, project_id: str) -> list[PortfolioEventRecord]:
        """Return all events for a project in chronological order."""
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, project_id, event_type, payload_json, created_at
                FROM project_events
                WHERE project_id = ?
                ORDER BY created_at ASC
                """,
                (project_id,),
            ).fetchall()
        return [
            PortfolioEventRecord(
                event_id=row["event_id"],
                project_id=row["project_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Test utility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all persisted data (for test isolation)."""
        with self._db.connect() as conn:
            conn.execute("DELETE FROM idempotency_keys")
            conn.execute("DELETE FROM factory_runs")
            conn.execute("DELETE FROM metrics_snapshots")
            conn.execute("DELETE FROM project_events")
            conn.execute("DELETE FROM build_briefs")
            conn.execute("DELETE FROM projects")

    def clear_factory_runs(self) -> None:
        """Clear factory run data and associated idempotency keys only.

        Unlike :meth:`reset`, this preserves project rows so that FK
        constraints on factory_runs continue to work after re-seeding.
        """
        with self._db.connect() as conn:
            conn.execute("DELETE FROM idempotency_keys")
            conn.execute("DELETE FROM factory_runs")

    # ------------------------------------------------------------------
    # Internal mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_project_record(row: Any) -> PortfolioProjectRecord:
        return PortfolioProjectRecord(
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"],
            status=LifecycleState(row["status"]),
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _to_factory_run_record(row: Any) -> FactoryRunRecord:
        return FactoryRunRecord(
            run_id=row["run_id"],
            project_id=row["project_id"],
            idea_id=row["idea_id"],
            status=row["status"],
            idempotency_key=row["idempotency_key"],
            dry_run=bool(row["dry_run"]),
            correlation_id=row["correlation_id"],
            repo_url=row["repo_url"],
            deploy_url=row["deploy_url"],
            error=row["error"],
            events=json.loads(row["events_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _default_transition_event(state: LifecycleState) -> str:
        mapping = {
            LifecycleState.REVIEW: "validated",
            LifecycleState.APPROVED: "approved",
            LifecycleState.BUILDING: "build_started",
            LifecycleState.LAUNCHED: "deployed",
            LifecycleState.SCALED: "decision_applied",
            LifecycleState.KILLED: "decision_applied",
        }
        return mapping.get(state, "state_transition")
