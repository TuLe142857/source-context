-- Track the commit whose indexing pipeline completed successfully.
-- Safe to apply more than once; existing branches remain uncheckpointed until reindexed.
ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS indexed_commit_sha VARCHAR(40);
