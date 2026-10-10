-- Persist GitHub's repository identity and delivery IDs for webhook matching
-- and idempotent processing. Safe to apply more than once.
ALTER TABLE repositories
    ADD COLUMN IF NOT EXISTS github_repository_id BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS ix_repositories_github_repository_id
    ON repositories (github_repository_id)
    WHERE github_repository_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS github_webhook_deliveries (
    delivery_id VARCHAR(128) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(100),
    status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
    job_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

ALTER TABLE github_webhook_deliveries
    ADD COLUMN IF NOT EXISTS job_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
