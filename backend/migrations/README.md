# Database migrations

Migrations are explicit SQL scripts. Application startup still calls
`Base.metadata.create_all()` for fresh installations; it does not upgrade an
existing schema.

For an existing PostgreSQL installation, take a backup, then apply scripts in
order with the deployment's PostgreSQL client. Migration `0002` adds the
checkpoint-validity bit and defaults existing rows to invalid, causing the next
indexing request to rebuild them safely. For example:

```powershell
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/0001_incremental_index_state.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/0002_indexing_checkpoint_valid.sql
```

The migration creates empty indexing state and run tables. Existing indexed
data is deliberately not assigned an `indexed_commit_sha`; those targets must
perform a full index before a checkpoint is recorded.

Rollback for migration `0001` removes only the newly introduced tables:

```sql
BEGIN;
DROP TABLE indexing_runs;
DROP TABLE indexing_states;
COMMIT;
```

Only roll back after stopping application versions that depend on these tables
and after backing up any run history that must be retained.
