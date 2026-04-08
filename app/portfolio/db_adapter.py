"""
db_adapter.py – Turso (libSQL) adapter with local SQLite fallback.

When ``TURSO_DATABASE_URL`` and ``TURSO_AUTH_TOKEN`` are configured the
adapter connects to the remote Turso database so that portfolio state
persists across Vercel cold starts.  Otherwise it falls back to the
standard ``sqlite3`` connection used for local development and testing.

The adapter exposes the same interface as :class:`PortfolioDB` so that
:class:`PortfolioRepository` can use it as a drop-in replacement.
"""

from __future__ import annotations

import logging
import sqlite3
import types
from pathlib import Path

logger = logging.getLogger(__name__)


def _try_import_libsql() -> types.ModuleType | None:
    """Attempt to import the ``libsql_experimental`` package.

    Returns the module or ``None`` if it is not installed.
    """
    try:
        import libsql_experimental  # type: ignore[import-untyped]

        return libsql_experimental
    except ImportError:
        return None


class TursoPortfolioDB:
    """Database helper that connects to Turso when credentials are present.

    Falls back to the standard ``sqlite3`` driver when the Turso SDK is
    not installed or credentials are not provided.
    """

    def __init__(
        self,
        *,
        db_path: str,
        schema_path: str | None = None,
        turso_database_url: str = "",
        turso_auth_token: str = "",
    ) -> None:
        self.db_path = db_path
        self.schema_path = (
            schema_path
            if schema_path is not None
            else str(Path(__file__).with_name("schema.sql"))
        )
        self._turso_url = turso_database_url
        self._turso_token = turso_auth_token
        self._use_turso = False

        libsql = _try_import_libsql()
        if libsql and self._turso_url and self._turso_token:
            self._libsql = libsql
            self._use_turso = True
            logger.info("TursoPortfolioDB: using Turso at %s", self._turso_url)
        else:
            self._libsql = None
            self._ensure_parent_dir()
            logger.info("TursoPortfolioDB: falling back to local SQLite at %s", self.db_path)

    def _ensure_parent_dir(self) -> None:
        """Create parent directory for file-backed databases."""
        if self.db_path == ":memory:":
            return
        path = Path(self.db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Return a connection configured for dict-like row access.

        Uses Turso's libSQL SDK when available, otherwise falls back to
        the standard ``sqlite3`` module.  The returned object is
        API-compatible with ``sqlite3.Connection``.
        """
        if self._use_turso and self._libsql is not None:
            connection = self._libsql.connect(
                self._turso_url,
                auth_token=self._turso_token,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        """Initialise database schema if not already present."""
        schema = Path(self.schema_path).read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema)
            self._apply_migrations(conn)

    @staticmethod
    def _apply_migrations(conn: sqlite3.Connection) -> None:
        """Apply incremental schema migrations for backwards compatibility."""
        columns = {row[1] for row in conn.execute("PRAGMA table_info(factory_runs)").fetchall()}
        if "correlation_id" not in columns:
            conn.execute("ALTER TABLE factory_runs ADD COLUMN correlation_id TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_factory_runs_correlation_id "
            "ON factory_runs(correlation_id)"
        )
