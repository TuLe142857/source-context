BEGIN;

CREATE TABLE indexing_states (
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    latest_observed_commit_sha VARCHAR(255),
    indexed_commit_sha VARCHAR(255),
    index_version VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'UNINDEXED',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, branch_id)
);

CREATE TABLE indexing_runs (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES indexing_jobs(id) ON DELETE SET NULL,
    base_commit_sha VARCHAR(255),
    target_commit_sha VARCHAR(255) NOT NULL,
    mode VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    current_stage VARCHAR(64),
    fallback_reason VARCHAR(512),
    error_message VARCHAR(2048),
    statistics JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_indexing_runs_workspace_id ON indexing_runs(workspace_id);
CREATE INDEX ix_indexing_runs_branch_id ON indexing_runs(branch_id);
CREATE INDEX ix_indexing_runs_job_id ON indexing_runs(job_id);
CREATE UNIQUE INDEX uq_indexing_runs_active_target
    ON indexing_runs(workspace_id, branch_id)
    WHERE status IN ('PENDING', 'QUEUED', 'RUNNING', 'RETRYING');

COMMIT;
