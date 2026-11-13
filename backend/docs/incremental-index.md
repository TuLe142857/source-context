# Incremental indexing

## Run selection

The indexing worker checks out the requested branch commit and compares it with
the last successful `IndexingState.indexed_commit_sha` for the workspace and
branch. A missing checkpoint selects `FULL`; a compatible checkpoint and a
valid non-empty Git diff select `INCREMENTAL`; an empty diff selects `NOOP`.
An incompatible index version or failed history comparison selects
`FULL_FALLBACK`. `force_full=true` on the branch or workspace trigger bypasses
diff selection and performs a complete rebuild.

Incremental runs parse only changed paths and remove deleted and old renamed
paths. The parser leaves unchanged Neo4j file records in place. SCIP and API
relationships are rebuilt from the complete current project graph so cross-file
references are refreshed. Vector records for unchanged files are preserved.

## Storage and checkpoints

Neo4j project data is replaced in one Neo4j transaction. Readers see the old
graph until transaction commit; a parser, SCIP, or API-map failure rolls the
replacement back. Source artifacts use content-addressed project/path keys.
New objects are uploaded before graph references change, and cleanup checks
Neo4j references before deleting an object.

Qdrant upserts changed-file vectors before deleting obsolete points. This makes
retries idempotent and avoids gaps during replacement. PostgreSQL advances the
successful commit only after the graph transaction, Qdrant reconciliation, and
S3 cleanup succeed. These stores do not share a distributed transaction: a
failure after Neo4j commit can temporarily leave Neo4j at the target commit and
Qdrant partially reconciled while the checkpoint remains at the prior commit.
Retrying the failed run replays the diff and converges the stores.

`checkpoint_valid` is set false durably immediately before graph replacement
and is restored only after all required stores finish. A reclaimed run with an
invalid checkpoint selects `FULL_FALLBACK`, including when a failed full reindex
was targeting the same SHA as the earlier checkpoint.

Workers hold a PostgreSQL connection-level global graph lock and a branch lock
for the full job. The global lock protects shared project graphs and S3
references across workspaces. It serializes indexing jobs.

## Existing data

An index version mismatch selects a full rebuild. New-format Qdrant records are
reconciled by workspace, branch, project, and path. During successful full
rebuilds, legacy points with workspace, branch, and file-path metadata are
removed only when their paths fall under rebuilt project roots. During
incremental runs, legacy points are removed only for exact changed/deleted
paths. Points missing enough target/path metadata are retained because their
owner cannot be identified safely; operators may need a separately reviewed
collection migration to retire those records.

Source artifacts referenced by the current Neo4j graph are retained. Replaced
artifacts are deleted after their last graph reference is removed. Legacy
unreferenced objects outside the new project prefixes cannot be attributed by
an automatic sweep and require a separately reviewed S3 cleanup.

## Deployment

Apply the SQL scripts in `backend/migrations` to existing PostgreSQL databases
before deploying code that uses indexing states and runs. Existing repositories
start without a checkpoint and therefore receive a full indexing run. Do not
apply migrations to production until the deployment has been reviewed and
backed up.
