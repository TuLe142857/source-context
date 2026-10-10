# Repository sync and incremental indexing plan

## Goal

Allow workspaces to index private GitHub repositories, keep tracked branches fresh after pushes, and update only source files affected by each change while preserving a consistent searchable snapshot.

## Work plan

### 1. Define branch/index state and commit checkpoints — implemented for single-workspace branch use; workspace-scope refinement required

- [x] Trace how branch SHAs, branch status, indexing jobs, and worker stages currently interact.
- [x] Define which commit SHA means “latest observed remotely” and which means “fully indexed”.
- [x] Add a separately persisted `indexed_commit_sha` and an idempotent migration path for existing databases.
- [x] Update it only after every required indexing stage completes successfully.
- [x] Make “already indexed” decisions compare the requested/current commit with the last successful indexed commit.
- [x] Expose both commit values in the API/UI where useful.
- [x] Run the existing backend unit suite (39 passed); it currently has no focused tests for commit checkpoint transitions.
- [ ] Add focused tests for success, failed indexing, and a remote push that arrives during an indexing job.
- [ ] Apply the SQL migration in the target environment before deploying the updated backend.
- [ ] Move latest/indexed commit and indexing status to `workspace_branches` before production use where one repository/branch can be attached to multiple workspaces. `Branch` and `Repository` are shared globally, but projects, search payloads, and installation permissions are workspace-scoped; a single checkpoint on `Branch` cannot represent indexing success independently for each workspace.

### 2. Support private GitHub repositories — core implementation complete; rollout and revocation policy pending

- [x] Confirm the frontend can install/manage the GitHub App and workspaces persist an installation ID.
- [x] Find that branch inspection is currently a standalone endpoint with no workspace context, so it cannot select or authorize the correct installation.
- [x] Find that clone/fetch and `git ls-remote` have no credential provider; the current public branch API silently falls back to guessed branch names on any error.
- [x] Add App ID/private key configuration and a short-lived installation-token provider.
- [x] Scope branch preview to a workspace, authorize workspace membership, and fetch branches with its GitHub App installation.
- [x] Pass ephemeral credentials into clone/fetch and remote SHA lookup without storing them in repository URLs or command arguments.
- [x] Return explicit errors for missing/revoked installation access, missing repository, rate limits, and GitHub/API outages.
- [x] Replace raw workspace ID install state with signed, expiring, one-time state and validate that the returned installation belongs to this GitHub App.
- [x] Require webhook signature validation and fail closed when the webhook secret is not configured.
- [ ] Define and implement permission removal behavior, including access revocation and cleanup policy for already-indexed data.
- [ ] Run focused automated tests and a manual integration check using a GitHub App installation with one private test repository.

### 3. Turn GitHub push webhooks into indexing triggers — core push path implemented; lifecycle recovery pending

- [x] Require `X-Hub-Signature-256` validation with a configured webhook secret.
- [x] Resolve repositories by GitHub's stable repository ID, with URL matching to backfill IDs for existing repositories, and match the exact branch ref.
- [x] Persist/deduplicate `X-GitHub-Delivery` and record job IDs before queueing work.
- [x] Queue tracked branches whose pushed SHA is not indexed; replay duplicate queued deliveries safely using a database job claim.
- [x] Coalesce a push arriving during a run into a follow-up indexing job after the current SHA is committed.
- [ ] Define and complete cleanup for deleted branches and removed/revoked repository permissions. Deleted-branch events currently mark tracked branches outdated and report that cleanup is required; their vectors/graph/source objects remain until cleanup is implemented.
- [ ] Add a periodic reconciliation process for missed webhook deliveries or broker messages.
- [ ] Add focused automated tests and validate delivery/replay behavior against a test GitHub App.
- [ ] Make delivery triggers and checkpoints workspace-scoped before enabling branches attached to multiple workspaces; a global branch status/checkpoint cannot represent independent workspace indexes.

Implementation note: indexing jobs and delivery rows commit before Celery publishing. Duplicate GitHub retries replay the recorded job IDs, while the worker claims each pending job under a row lock to prevent duplicate execution. A periodic reconciler is still needed for cases where no retry arrives.

### 4. Connect incremental parsing/chunking to production indexing

- Fetch the target commit while retaining the last successful indexed commit as the diff base.
- Build a repository snapshot and use existing content hashes to parse/chunk added and modified files only.
- Preserve unchanged files; create explicit delete operations for removed/renamed files.
- Replace vectors, graph nodes/edges, and stored source objects for changed files; remove all corresponding old data for deleted files.
- Identify which SCIP/call-graph steps can be scoped to changed files and which require a project/branch rebuild when dependencies change.
- Keep a full reindex path for first indexing, invalid/missing checkpoints, parser/index schema changes, and recovery.

Before implementing the production incremental pipeline, move commit and status checkpoints to `workspace_branches`. Repository and branch models are shared, while projects, search results, and GitHub installation permissions are workspace-scoped; storing one checkpoint on `Branch` cannot represent each workspace's successful index independently.

Current findings for the next implementation phase:

- The repository scanner already computes SHA-256 fingerprints, and `RepositoryParserService` can parse only added/modified files while detecting deletions from a prior path-to-hash snapshot.
- `RepositoryChunkingService` chunks only that parse batch, and `IndexingDocumentBuilder` already produces deterministic documents and per-file replace/delete operations.
- Those APIs have no production callers in the task pipeline. `execute_branch_indexing_pipeline` still recursively parses every file, builds SCIP/call graph for each full project, and embeds all parsed nodes.
- The production stores are not yet safe for file replacement: Qdrant only upserts and its payload has no content revision; Neo4j file nodes receive fresh IDs and new S3 objects without removing prior nodes/objects; the current full-project SCIP graph builder creates references without first reconciling stale edges.
- There is no durable per-branch/project file manifest to supply `previous_hashes`. Add one keyed by branch, project, and repository-relative path and advance it only after the target stores finish successfully, alongside `indexed_commit_sha`.
- Since PostgreSQL, Qdrant, Neo4j, and S3 do not share a transaction, plan staged writes by revision and switch the active revision only after all required stores succeed; then garbage-collect the prior revision. Keep full reindex as the recovery path.

Recommended implementation order: (1) persist a successful per-project file manifest and expose a pure Git diff/snapshot input to the existing parser/chunker/builder; (2) add provider adapters for deterministic Qdrant point replacement and file-scoped Neo4j/S3 cleanup; (3) keep SCIP as a project-level rebuild initially because symbol changes can affect references outside the edited files; (4) publish a revision only when every stage succeeds; (5) add fast paths for deletion-only and no-op commits, then evaluate narrower SCIP updates.

### 5. Reliability, access control, and operations

- Make job creation/worker execution idempotent and add bounded retries with actionable failure reasons.
- Avoid exposing private-repository source or search results across workspaces/users; verify authorization at retrieval boundaries.
- Show last indexed commit, latest known commit, last successful run, current job, and failure details.
- Track changed/unchanged/deleted file counts, durations, embedding usage/cost, and full-reindex reasons.
- Set and validate size/time limits for large repositories and files.

## Step 1 findings and state contract

Current implementation findings:

- `branches.commit_hashed` is populated from `git ls-remote` during repository attachment and overwritten with the fetched HEAD in `download_branch_source_stage`. It therefore describes the latest known/fetched commit, not a reliable “fully indexed” checkpoint.
- The worker currently updates `commit_hashed` before parsing, graph building, and embeddings finish. A later failure can leave the branch SHA advanced even though indexing failed.
- `IndexingService.trigger_branch_indexing` fetches a remote SHA but does not use it in its decision. It rejects any branch whose status is `INDEXED`, without checking whether the remote SHA differs.
- Push webhooks only set `INDEXED` branches to `OUTDATED`; they do not create an indexing job. Signature verification is skipped when the secret is empty.
- The ORM starts with `Base.metadata.create_all`, and the repository has no migration framework or tracked database migrations. `create_all` does not add a new column to an existing table, so adding the indexed checkpoint requires an explicit existing-database migration and deployment procedure.

Target semantics:

- `commit_hashed`: latest commit SHA observed from GitHub or fetched from the remote branch.
- `indexed_commit_sha`: commit SHA whose indexing pipeline completed successfully and whose search/graph data is the active snapshot.
- `indexing_status`: operational summary; `INDEXED` means the two SHAs match and the active snapshot completed, `OUTDATED` means the remote SHA differs from the indexed checkpoint, `INDEXING` means a job is active, and `FAILED` means the latest attempted update failed. The indexed checkpoint remains unchanged on failure.
- Initial indexing has no `indexed_commit_sha`; it becomes set only after a successful complete pipeline. If the remote branch advances while a job runs, completion records the SHA actually processed and the branch remains `OUTDATED` against the newer remote SHA.

## Validation targets

- Existing repositories can be upgraded without losing branch/job data.
- A failed indexing job never advances `indexed_commit_sha`.
- A successful job records the exact SHA it indexed, even if the remote advances during the job.
- Re-triggering an already-current branch is idempotent; a changed remote SHA can be indexed.
- Private access credentials never appear in stored URLs, logs, or API responses.
- Duplicate webhook deliveries do not create duplicate jobs.
- Changed files are replaced, deleted files are removed, and unchanged files keep their current index entries.

## Step 2 findings and implementation contract

- The workspace page already installs/manages a GitHub App and stores `github_installation_id`; installation webhook events already use that ID to add repositories.
- There is no backend GitHub App ID or private key setting and no code that exchanges an App JWT for an installation access token.
- The branch preview endpoint currently receives only a repository URL. It must receive a workspace ID and authorize the caller before using that workspace's installation.
- `fetch_github_branches` currently uses an unauthenticated public API request and falls back to `main`/`master` on all errors. `get_latest_commit_hash` uses unauthenticated `git ls-remote`; the clone/fetch client has no credential input.
- The same short-lived installation token provider should support GitHub API branch/commit lookups and Git clone/fetch. Credentials must remain transient, scoped to the installation, and absent from stored URLs and logs.
- Existing public repositories should continue to work without an installation. Private repository operations should fail with a clear “connect or grant this repository to the workspace's GitHub App” error when no installation access is available.
- The workspace-to-installation callback originally trusted a numeric workspace ID in `state`; it now validates signed, expiring, one-time state issued only after workspace access is checked.
- Implemented an App JWT/installation-token client, workspace-scoped branch lookup, authenticated branch SHA lookup, and Git clone/fetch authentication through a child-process HTTP header configuration. The short-lived token remains in process memory only and is never included in the clone URL, Git arguments, or API output.
- The frontend now requests a short-lived install state from the backend before opening the GitHub App installation page. Callback handling consumes the nonce from Redis and checks the installation's App ID before linking it to the workspace.
- Set `SOURCE_CONTEXT_GITHUB_APP_ID`, `SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET` on both backend and worker; configure the GitHub App with Contents read permission and the required setup/webhook URLs before enabling private repository use.
