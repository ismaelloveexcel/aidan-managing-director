"""Persistent factory run store backed by PortfolioRepository.

Replaces the in-memory FactoryRunStore so that factory run state
survives Vercel serverless cold starts. Provides the same interface
that FactoryOrchestrator and CommandCenterService expect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.factory.models import FactoryRunResult, FactoryRunStatus

if TYPE_CHECKING:
    from app.portfolio.models import FactoryRunRecord
    from app.portfolio.repository import PortfolioRepository


def _record_to_result(record: "FactoryRunRecord") -> FactoryRunResult:
    """Map a persisted FactoryRunRecord back to FactoryRunResult."""
    return FactoryRunResult(
        run_id=record.run_id,
        project_id=record.project_id,
        idea_id=record.idea_id,
        status=FactoryRunStatus(record.status),
        idempotency_key=record.idempotency_key,
        dry_run=record.dry_run,
        correlation_id=record.correlation_id,
        repo_url=record.repo_url,
        deploy_url=record.deploy_url,
        error=record.error,
        events=record.events,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class PersistentFactoryRunStore:
    """Drop-in replacement for FactoryRunStore backed by PortfolioRepository.

    Implements the same public interface (get_by_run_id, get_by_idempotency_key,
    get_by_correlation_id, upsert, list_runs, reset) so FactoryOrchestrator
    and CommandCenterService can use it without changes.
    """

    def __init__(self, repository: "PortfolioRepository") -> None:
        self._repo = repository

    def get_by_run_id(self, run_id: str) -> FactoryRunResult | None:
        record = self._repo.get_factory_run(run_id)
        return _record_to_result(record) if record else None

    def get_by_idempotency_key(self, key: str) -> FactoryRunResult | None:
        record = self._repo.get_factory_run_by_idempotency_key(key)
        return _record_to_result(record) if record else None

    def get_by_correlation_id(self, correlation_id: str) -> FactoryRunResult | None:
        record = self._repo.get_factory_run_by_correlation_id(correlation_id)
        return _record_to_result(record) if record else None

    def upsert(self, run: FactoryRunResult) -> None:
        self._repo.save_factory_run(run)

    def list_runs(self) -> list[FactoryRunResult]:
        records = self._repo.list_factory_runs(limit=500)
        return [_record_to_result(r) for r in records]

    def reset(self) -> None:
        """Clear factory run data only (for tests).

        Unlike ``PortfolioRepository.reset()`` which clears *everything*,
        this only deletes factory_runs and associated idempotency_keys
        so that project rows survive.
        """
        with self._repo._db.connect() as conn:
            conn.execute("DELETE FROM idempotency_keys")
            conn.execute("DELETE FROM factory_runs")
