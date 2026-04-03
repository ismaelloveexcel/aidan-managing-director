"""
SQLite connection and schema bootstrap utilities for portfolio storage.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class PortfolioDB:
    """Small SQLite helper that initialises and serves database connections."""

    def __init__(self, db_path: str, schema_path: str | None = None) -> None:
        self.db_path = db_path
        self.schema_path = (
            schema_path
            if schema_path is not None
            else str(Path(__file__).with_name("schema.sql"))
        )
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        """Create parent directory for file-backed databases."""
        if self.db_path == ":memory:":
            return
        path = Path(self.db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Return a connection configured for dict-like row access."""
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        """Initialise database schema if not already present."""
        schema = Path(self.schema_path).read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema)
