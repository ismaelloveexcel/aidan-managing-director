PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS build_briefs (
    brief_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    brief_hash TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    validation_score REAL NOT NULL DEFAULT 0.0,
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    monetization_model TEXT NOT NULL DEFAULT '',
    deployment_plan_json TEXT NOT NULL DEFAULT '{}',
    launch_gate_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_build_briefs_project_id
    ON build_briefs(project_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_build_briefs_idempotency_key
    ON build_briefs(idempotency_key);

CREATE TABLE IF NOT EXISTS project_events (
    event_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_events_project_id_created_at
    ON project_events(project_id, created_at);

CREATE TABLE IF NOT EXISTS metrics_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    visits INTEGER NOT NULL,
    signups INTEGER NOT NULL,
    revenue REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    conversion_rate REAL NOT NULL,
    timestamp TEXT NOT NULL,
    raw_payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metrics_project_id_timestamp
    ON metrics_snapshots(project_id, timestamp);

CREATE TABLE IF NOT EXISTS factory_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    idea_id TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 1,
    correlation_id TEXT,
    repo_url TEXT,
    deploy_url TEXT,
    error TEXT,
    events_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_factory_runs_project_id_created_at
    ON factory_runs(project_id, created_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
