# Frontend Development Plan — Source Context

## Context

Backend (`openapi.json`, source of truth) models a **Workspace → Repository → Branch → Project (sub-project/SCIP target)** hierarchy plus account/token management. The current frontend (`frontend/src/`) only implements a shell built around a concept it calls "Project" — but that concept actually corresponds to the backend's **Workspace**. Backend's real "Project" (a `root_dir` + `language` SCIP target nested under a Branch) doesn't exist in the frontend at all, and Repository/Branch aren't modeled as separate entities either.

Scope for this plan: **account management, workspace, and workspace configuration (repository, branch, sub-project)**. MCP endpoints, graph browsing, and vector/semantic search are explicitly **out of scope** (candidate for a later, separate plan). Indexing trigger/status (workspace/branch level) is **in scope**.

The backend does not yet use a unified response envelope on its REST surface (only the `/mcp/v1/*` routes currently wrap responses in `ResponseSuccessSchema`/`ResponseErrorSchema`), but `backend/app/core/response.py` + `backend/app/core/error_code.py` define the target shape it will migrate to. The frontend's API layer is designed now so that migration is a one-file change later, not a rewrite.

Goal: fix the terminology mismatch, build a clean API/UI-separated architecture, cover the full account/workspace/repository/branch/project configuration surface, and provide clearly-marked UI templates (with stub API hooks) for functionality the product will obviously need but the backend doesn't expose yet.

**Status: Phases 0–10 below were implemented and verified** (build/typecheck/lint clean, full browser E2E pass against the live dev stack — register/login, workspace CRUD, real GitHub repo attach, sub-project config, branch reindex, PAT create/revoke, template pages all confirmed working).

**Status: Migration Plan — Round 2 (below) implemented and verified** — Steps A–E all complete, build/typecheck/lint clean, full browser E2E re-pass against the live dev stack confirmed: remove-member (real), edit sub-project (real), branch reindex with commit override, new Branches flat/filterable view, and workspace rename correctly demoted to template (badge + error toast, no fake success).

**Bug found during Round 2 verification (backend-side, not fixed here per "don't touch backend"):** `GET /branches/{workspace_id}/hierarchy` returns `members: []` even when members genuinely exist — confirmed by comparing directly against `GET /workspaces/{workspace_id}/members`, which returns the correct list (including the owner). **Frontend workaround applied**: the Members tab and the workspace detail header's member count now source from `useWorkspaceMembersQuery` (`GET /workspaces/{id}/members`, always correct) instead of `hierarchy.members` (broken). `WorkspaceHierarchyResponse.members` is effectively unused by the frontend now — worth removing from the schema or fixing backend-side whenever that router gets touched next.

## Backend Change Log — Round 2 (`openapi.json` re-verified against current implementation)

The backend API changed after the initial implementation. Re-analysis of `openapi.json` found:

1. **Response envelope is now live on every `/api/v1/*` endpoint** (previously only `/mcp/v1/*` used it). Every success response is `{success, data, message}`, every error is `{success:false, error_code, message}` (422 validation errors remain FastAPI's raw `{detail:[...]}` shape, unwrapped). **No code change needed** — `src/api/http.ts`'s interceptor was already written to detect and unwrap this shape transparently; it was validated against the old (raw-payload) API and now also matches the new (enveloped) one with zero changes.
2. **Repository/Branch/Project/Indexing endpoints moved routers** — off `/api/v1/workspaces/{id}/...` onto two new dedicated routers:
   - `/api/v1/branches/*` — repositories, branches, sub-projects, hierarchy.
   - `/api/v1/indexing/*` — trigger + job listing.
   Every path segment referencing these in `src/api/*.api.ts` needs updating (see table below).
3. **`PATCH /api/v1/workspaces/{id}` (workspace rename/description) was removed entirely** — the `WorkspaceUpdate` schema is gone from the spec. This is a real regression vs. what was built; **downgraded from real to template** per product decision (keep the edit form, badge it "Sắp có", stub the API — consistent with how every other missing endpoint is handled).
4. **`DELETE /api/v1/workspaces/{id}/members/{user_id}` now exists** — remove-member is real. **Promoted from template to real.**
5. **`PATCH /api/v1/branches/{workspace_id}/projects/{project_id}` now exists** (`ProjectUpdateRequest{root_dir?, language?}`) — update sub-project is real. **Promoted from template to real.**
6. **`POST /api/v1/branches/remote-branches`** (was `.../workspaces/{id}/repositories/inspect-branches`) no longer takes `workspace_id` at all — it's a standalone GitHub-URL-in, branches-out utility, decoupled from any workspace.
7. **`MemberResponse` gained `workspace_id` and `full_name`** (nullable) — `project_id` naming artifact still present, kept opaque as before.
8. **`AddMemberRequest`** now accepts `{email?, user_id?}` (either, not just email) — not built this round per product decision (email-only flow stays as the sole path for now).
9. **New `GET /api/v1/branches/{workspace_id}/workspace-branches?repository_id=`** — flat list of a workspace's branches, optionally filtered by repository. Not present before. **Adopted this round** for a new "Branches" view (see Pages & Features).
10. **`POST /api/v1/indexing/{workspace_id}/branch/{branch_id}`** now accepts an optional body `TriggerBranchIndexingRequest{commit_hashed?}` and documents `409` conflict responses (`ACTION_CONFLICT`/`ACTION_ALREADY_PERFORMED`) for re-triggering an in-flight job. **Adopted this round** — reindex dialog gets an optional commit-hash field; 409s surface via the existing `ApiError`/toast path with no special-casing needed (backend's `message` is already user-facing).
11. `CreateWorkspaceRequest` (renamed from `WorkspaceCreate`) and `VectorSearchRequest` (renamed from `SearchRequest`, out of scope) — cosmetic schema renames, no field changes.
12. `/api/v1/users/*` dev/test scaffolding endpoints removed entirely — already out of scope, no impact.
13. Everything else (`WorkspaceResponse`, `BranchResponse`, `RepositoryResponse`, `ProjectResponse`, `BranchCreateRequest`, `RepositoryCreateRequest`, `SourceLanguage`, `BranchIndexingStatus`, `PATResponse`/`PATCreateRequest`/`PATCreateResponse`, `TokenResponse`, `UserResponse`, `error_code.py`) is **unchanged**.

## Confirmed Decisions

- **UI components**: shadcn/ui (Radix primitives + Tailwind v4), keeping the existing dark glassmorphism tokens in `index.css` as the theme base.
- **Icons**: `lucide-react` (already installed).
- **Routing**: `react-router-dom` — real URLs per entity.
- **HTTP client**: `axios` (replaces the hand-rolled `fetch` wrapper in `src/services/api.ts`), via a single configured instance with interceptors.
- **Server state**: `@tanstack/react-query` — all API data (queries + mutations), including cache invalidation on mutation success.
- **Client/global state**: `@reduxjs/toolkit` — reserved for state that is *not* server cache: auth session (user, token), and cross-cutting UI state (toasts, active modal, global loading flags). Server data (workspaces, repos, etc.) stays in React Query's cache only — it must not be duplicated into Redux, to avoid the classic dual-cache sync bugs.
- **Styling**: Tailwind v4 (already installed), via shadcn's CSS-variable theming.

## API Endpoint Scope (what the FE calls vs. excludes)

| Group | Example paths | FE builds against it? |
|---|---|---|
| Health | `/health`, `/api/v1/health` | Not user-facing; skip. |
| Auth | `/api/v1/auth/register`, `/login`, `/me` | **Yes** — core. |
| Auth — MCP token | `/api/v1/auth/token` (custom token, "e.g. for MCP server auth") | **No** — MCP-server-oriented, not an end-user account feature. Not built this round. |
| Users (dev/test scaffolding) | `/api/v1/users/*` (`test-db`, list, create, get-by-id) | **No** — unauthenticated dev/test endpoints, not real account management. |
| Personal Access Tokens | `/api/v1/user/tokens/*` | **Yes** — full CRUD, this is the account's "API Keys" page. |
| Workspaces | `/api/v1/workspaces/*` (create/get/delete/members) | **Yes** — core. No update endpoint anymore (see Change Log #3). |
| Branches (repositories, branches, sub-projects, hierarchy) | `/api/v1/branches/*` (moved off `/workspaces/{id}/...`, see Change Log #2, #6, #9) | **Yes** — core. |
| Indexing | `/api/v1/indexing/*` (moved off `/workspaces/{id}/...`, see Change Log #2, #10) | **Yes** — core. |
| Vector search | `/api/v1/vector/search/*` | **No** — explicitly out of scope per product decision. |
| MCP (`/mcp/v1/*`) — graph, vector, general | all | **No** — explicitly out of scope; these are tool-call surfaces for the MCP server/CLI, not the web frontend. |

## Terminology Alignment (critical — apply everywhere)

| Current frontend | Correct backend term | Notes |
|---|---|---|
| `Project` / `project_name` | **Workspace** / `workspace_name` | Rename type, service, components, routes. `WorkspaceResponse` has no `created_at`/`updated_at`. |
| `ProjectDetail` (ad-hoc combine of members+repos) | **`WorkspaceHierarchyResponse`** (`GET /workspaces/{id}/hierarchy`) | Single endpoint returns `members[]` + `repositories[].branches[].projects[]` — use it instead of manual joins. |
| `RepositoryLink` (`description`, `default_branch`, `status`, `created_at` on repo) | **`RepositoryResponse`** (`id`, `name`, `git_url`, `branches: BranchResponse[]`) | Repo itself has none of those fields — status lives per-**Branch** (`BranchResponse.indexing_status`). |
| (not modeled) | **Branch** (`BranchResponse`: `id`, `repository_id`, `branch_name`, `commit_hashed`, `indexing_status`, `local_path`, `projects`) | New entity to build UI for. |
| (not modeled) | **Project** = sub-project/SCIP target (`ProjectResponse`: `id`, `branch_id`, `workspace_id`, `root_dir`, `language: SourceLanguage`) nested under Branch | Label as "Sub-project" in UI copy to avoid re-confusing with Workspace. |
| `Member` (`role`, `user_email`, `user_username`) | **`MemberResponse`** (`project_id` *(sic — this field is actually the workspace-membership id, an apparent backend naming artifact; treat opaquely, don't rename it client-side)*, `user_id`, `email?`, `username?`, no role) | Frontend invented an RBAC concept the backend doesn't have — dropped per prior decision. |

## API Response Envelope Readiness (types to build now)

Mirror `backend/app/core/response.py` / `error_code.py` in `src/api/types/common.ts`, even though most `/api/v1/*` REST endpoints currently return raw payloads (only `/mcp/v1/*` — out of scope — uses the envelope today):

```ts
export interface PaginationMeta {
  current_page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  message: string | null;
}

export interface ApiPaginationResponse<T> {
  success: true;
  data: T[];
  message: string | null;
  meta: PaginationMeta;
}

export interface ApiErrorResponse {
  success: false;
  error_code: ErrorCode;
  message: string | null;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

// values match ErrorCode.error_code strings in backend/app/core/error_code.py exactly
export enum ErrorCode {
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  UNAUTHORIZED_ERROR = 'UNAUTHORIZED_ERROR',
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  JWT_TOKEN_REVOKED = 'JWT_TOKEN_REVOKED',
  JWT_TOKEN_EXPIRED = 'JWT_TOKEN_EXPIRED',
  JWT_TOKEN_NOT_FRESH = 'JWT_TOKEN_NOT_FRESH',
  INVALID_JWT_TOKEN = 'INVALID_JWT_TOKEN',
  LOGIN_FAILED = 'LOGIN_FAILED',
  FORBIDDEN = 'FORBIDDEN',
  USER_NOT_ACTIVE = 'USER_NOT_ACTIVE',
  BAD_REQUEST = 'BAD_REQUEST',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_CODE = 'INVALID_CODE',
  CODE_EXPIRED = 'CODE_EXPIRED',
  ACTION_ALREADY_PERFORMED = 'ACTION_ALREADY_PERFORMED',
  ACTION_CONFLICT = 'ACTION_CONFLICT',
  RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND',
  RESOURCE_ALREADY_EXISTS = 'RESOURCE_ALREADY_EXISTS',
  RESOURCE_CONFLICT = 'RESOURCE_CONFLICT',
  RESOURCE_NOT_AVAILABLE = 'RESOURCE_NOT_AVAILABLE',
  RESOURCE_IN_USE = 'RESOURCE_IN_USE',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  DATA_INTEGRITY_ERROR = 'DATA_INTEGRITY_ERROR',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  UNSUPPORTED_FILE_TYPE = 'UNSUPPORTED_FILE_TYPE',
  FILE_UPLOAD_FAILED = 'FILE_UPLOAD_FAILED',
}
```

Also define a client-side `ApiError` class (`code: ErrorCode | 'VALIDATION_ERROR'`, `message: string`, `fieldErrors?: Record<string, string>` for `HTTPValidationError` payloads) — this is what the axios error interceptor throws, so every `useMutation`'s `onError` deals with one consistent shape regardless of whether the backend returned the old raw-`detail` style or the new envelope.

**Axios response interceptor logic** (`src/api/http.ts`):
- Success: if `response.data` has a boolean `success` field → unwrap `.data` (future envelope format); otherwise return `response.data` as-is (current raw-payload format). This makes the switch transparent whenever the backend migrates a given endpoint.
- Error: if `error.response.data` matches `ApiErrorResponse` (`success: false`) → throw `ApiError` from `error_code`/`message`; else if it matches `HTTPValidationError` (`{detail: [...]}`, today's FastAPI default) → throw `ApiError` with `code: 'VALIDATION_ERROR'` and per-field messages from `detail[].loc`/`msg`; else throw a generic `ApiError` with `code: ErrorCode.UNKNOWN_ERROR`.
- On HTTP 401 → dispatch Redux `authSlice.logout()` and redirect to `/login`.

## Known Backend Spec Quirks / Gaps (verified directly against `openapi.json`, updated Round 2)

- `UserResponse.is_active` is typed as **string**, not boolean.
- **No workspace update endpoint at all anymore** (PATCH removed, `WorkspaceUpdate` schema gone) — rename/description edit downgraded to template.
- No self-service "leave workspace" (remove-member itself is now real, see Change Log #4).
- No endpoint to add a branch to an **already-existing** repository — branches are only registered together with the repo at creation time (`RepositoryCreateRequest.branches`).
- No update (PATCH/PUT) endpoint for Repository or Branch — create + delete only. (Project/sub-project update is now real, see Change Log #5.)
- Indexing can be triggered at **workspace** level (`POST /indexing/{id}`) or **branch** level (`POST /indexing/{id}/branch/{branchId}`, optional `commit_hashed` override) — still no project-level reindex endpoint.
- `GET /workspaces` pagination is `skip`/`limit` query params only, returning a plain array — no total-count metadata, so a page-number UI isn't possible until the backend adopts `ApiPaginationResponse`.
- No change-password, forgot-password, or update-own-profile endpoints exist at all.
- Collection endpoints use the no-trailing-slash form consistently now (duplicates removed backend-side).
- `IndexingJobResponse.status` is a free string, not formally tied to the `BranchIndexingStatus` enum — confirmed still true, e.g. real values observed include `DOWNLOADING_SOURCE`.
- Response envelope (`{success, data, message}` / `{success:false, error_code, message}`) is now **live on every `/api/v1/*` endpoint**, not just future-proofing — see Change Log #1.

## Missing-API Items → Build as UI Template + Stub Hook (per product decision)

These are **not** wired to any real endpoint. Each gets a real UI (form/button/page) and a stub API function + React Query hook living in a clearly separated `*.template.ts` file, so swapping in the real call later is a one-line import change. UI must visibly indicate these aren't live yet (e.g. a small "coming soon" badge or disabled+tooltip state is acceptable, but the flow itself should be fully clickable/demoable).

**Updated Round 2**: Project/sub-project update and remove-member are now real (moved OUT of this table, into the live API). Workspace rename/description moved IN (backend removed the endpoint).

| Feature | Template location | Notes |
|---|---|---|
| Update Repository (rename), Update Branch (re-point `commit_hashed`) | `src/api/repositories.template.ts`, `branches.template.ts` | Edit forms reuse the same fields as the create forms. |
| **Update Workspace (rename/description)** *(new this round — was real, backend removed `PATCH /workspaces/{id}`)* | `src/api/workspaces.template.ts` | Overview tab keeps the edit form, badged "Sắp có", stubbed instead of calling a now-nonexistent endpoint. |
| Add branch to an existing repository | `src/api/repositories.template.ts` | Separate from the real "attach repository" 2-step flow. |
| Reindex a single Project (sub-project) | `src/api/projects.template.ts` | Per decision: kept as its own template action, distinct from the real branch/workspace-level reindex buttons (which call real endpoints). |
| Change password, forgot/reset password, edit own profile (username/full_name/email) | `src/api/account.template.ts` | Pages: `/settings/security`, `/forgot-password`, `/reset-password`, `/settings/profile`. |
| Leave workspace (self) | `src/api/workspaces.template.ts` | Remove-member (owner action) is now real — see Pages & Features. |
| Add member by `user_id` (alternative to email) | *(not built — deferred)* | Backend's `AddMemberRequest` now accepts `{email?, user_id?}`; product decision this round was to keep the email-only flow and defer this. |

## Pages & Features (updated Round 2)

**Live (real API):**
1. `/login`, `/register` — auth forms.
2. Logout — action only (clears Redux session + axios auth header), no dedicated page.
3. `/settings/tokens` — Personal Access Tokens: list, create (show `raw_token` once, copy button, warning), revoke.
4. `/workspaces` — list of own/member workspaces (`GET /workspaces`), create-workspace modal.
5. `/workspaces/:workspaceId` — detail, built from `GET /branches/{id}/hierarchy` *(moved router)*:
   - Overview: **name/description now read-only** (no backend endpoint — see template list), delete workspace (owner-only).
   - Members: list + add-by-email + **remove member (owner action) — now real** *(new this round)*.
   - Repositories: list, each showing nested branches → nested sub-projects; "Add repository" 2-step flow (inspect-branches via `POST /branches/remote-branches` → create with selected branches); delete repository/branch/project; create sub-project (root_dir + language) under a branch; **edit sub-project (root_dir/language) — now real** *(new this round)*.
   - Indexing: trigger workspace-level or per-branch reindex — **branch reindex gains an optional "at specific commit" field** *(new this round, `TriggerBranchIndexingRequest.commit_hashed`)*; indexing-jobs panel with live status/progress (polling while any job is in-flight); 409 conflict on double-trigger surfaces via the existing toast/`ApiError` path, no special-casing needed.
6. **New: Branches view** *(new this round)* — flat, workspace-scoped branch list via `GET /branches/{id}/workspace-branches`, filterable by repository (`?repository_id=`), as a section/tab alongside the nested Repositories view.

**Template-only (UI + stub hook, no live API):**
7. `/settings/profile` — edit profile.
8. `/settings/security` — change password.
9. `/forgot-password`, `/reset-password` — password recovery flow.
10. Workspace detail → Overview tab rename/description form *(demoted this round — was real)* + "Leave workspace" button (member row "Remove" is now real, see above).
11. Repository/Branch rows → "Edit" action *(Project/sub-project row "Edit" is now real, see above)*.
12. Repository detail → "Add branch to existing repository" action.
13. Sub-project row → "Reindex this project" button (branch-level reindex is real, see above).

## Folder Structure

```
src/
├── api/
│   ├── http.ts                     # axios instance + request/response interceptors (auth header, envelope unwrap, ApiError normalization, 401 handling)
│   ├── types/
│   │   ├── common.ts                # ApiResponse<T>, ApiPaginationResponse<T>, PaginationMeta, ErrorCode, ApiError
│   │   ├── auth.ts                  # UserResponse, TokenResponse
│   │   ├── tokens.ts                # PATResponse, PATCreateRequest, PATCreateResponse
│   │   ├── workspace.ts             # WorkspaceResponse, CreateWorkspaceRequest, WorkspaceHierarchyResponse, MemberResponse (+workspace_id, +full_name), AddMemberRequest — WorkspaceUpdate REMOVED (Round 2: no backend endpoint)
│   │   ├── repository.ts            # RepositoryResponse, RepositoryCreateRequest, RemoteBranchesResponse, InspectGitHubBranchesRequest
│   │   ├── branch.ts                # BranchResponse, BranchCreateRequest, BranchIndexingStatus
│   │   ├── project.ts               # ProjectResponse, ProjectCreateRequest, SourceLanguage, +ProjectUpdateRequest (Round 2: new, real)
│   │   └── indexing.ts              # IndexingJobResponse, +TriggerBranchIndexingRequest (Round 2: new, optional commit_hashed)
│   ├── auth.api.ts                  # login, register, getMe — real
│   ├── tokens.api.ts                # PAT CRUD — real
│   ├── workspaces.api.ts            # workspace create/get/delete + members(add/list) — real; +removeMember (Round 2: promoted from template)
│   ├── workspaces.template.ts       # leaveWorkspace — stub; +updateWorkspace (Round 2: demoted from real — backend removed PATCH)
│   ├── repositories.api.ts          # inspect-branches (`POST /branches/remote-branches`, Round 2: path moved, no workspace_id param), create/delete (`/branches/{workspaceId}/repositories...`, Round 2: path moved) — real
│   ├── repositories.template.ts     # updateRepository, addBranchToRepository — stub
│   ├── branches.api.ts              # delete (`/branches/{workspaceId}/{branchId}`, Round 2: path moved), +listWorkspaceBranches (Round 2: new `GET /branches/{workspaceId}/workspace-branches`) — real; getWorkspaceHierarchy also lives here or in workspaces.api.ts (`GET /branches/{workspaceId}/hierarchy`, Round 2: path moved)
│   ├── branches.template.ts         # updateBranch — stub
│   ├── projects.api.ts              # create/delete (`/branches/{workspaceId}/...`, Round 2: path moved), +updateProject (Round 2: promoted from template, `PATCH /branches/{workspaceId}/projects/{projectId}`) — real
│   ├── projects.template.ts         # reindexProject — stub (updateProject REMOVED — promoted to real, see projects.api.ts)
│   ├── indexing.api.ts              # trigger workspace index (`POST /indexing/{workspaceId}`, Round 2: path moved), list jobs (`GET /indexing/{workspaceId}/jobs`, Round 2: path moved), +triggerBranchIndex (Round 2: moved in from branches.api.ts, now `POST /indexing/{workspaceId}/branch/{branchId}` with optional `commit_hashed` body) — real
│   └── account.template.ts          # changePassword, forgotPassword, resetPassword, updateProfile — stub
├── hooks/                           # React Query hooks — the ONLY thing components import for data
│   ├── useAuth.ts
│   ├── useTokens.ts
│   ├── useWorkspaces.ts             # wraps both workspaces.api.ts and workspaces.template.ts
│   ├── useRepositories.ts
│   ├── useBranches.ts
│   ├── useProjects.ts
│   ├── useIndexing.ts
│   └── useAccount.ts                # template-only
├── store/
│   ├── index.ts                     # configureStore
│   ├── authSlice.ts                 # session user/token, persisted to localStorage, logout()
│   └── uiSlice.ts                   # toasts, active modal/dialog state
├── pages/                           # route-level components (one per route in Pages & Features)
├── components/
│   ├── ui/                          # shadcn primitives
│   └── ...                          # feature components: WorkspaceCard, MemberList, RepositoryTree, BranchRow, ProjectForm, IndexingJobsPanel, etc.
├── routes/
│   ├── router.tsx                   # react-router route table
│   └── ProtectedRoute.tsx           # redirects to /login if no session
├── lib/
│   ├── cn.ts                        # shadcn class-merge util
│   └── queryClient.ts
├── App.tsx
└── main.tsx
```

**Separation rule**: `components/` and `pages/` never import from `api/` directly — only from `hooks/`. `hooks/` never talk to Redux for server data, only React Query. `store/` never holds server entities, only session + UI state. This is what makes future backend contract changes (e.g. the envelope migration) a `api/`-and-`hooks/`-only change with zero UI edits.

## Phases

**Phase 0 — Tooling & Foundation**
Install `axios`, `@tanstack/react-query` (+ devtools), `@reduxjs/toolkit`, `react-redux`, `react-router-dom`, shadcn/ui deps (`class-variance-authority`, `clsx`, `tailwind-merge`); `npx shadcn@latest init` wired to existing CSS variables. Scaffold the folder structure above. Wire `QueryClientProvider`, `ReduxProvider`, `BrowserRouter` into `main.tsx`.

**Phase 1 — API Response Types & HTTP Layer**
Build `src/api/types/common.ts` (envelope types above) and `src/api/http.ts` (axios instance + interceptors + `ApiError`).

**Phase 2 — Domain Types & Real API Modules**
Build `src/api/types/*.ts` mirroring backend schemas exactly (tables above), then `*.api.ts` modules calling the confirmed real endpoints only.

**Phase 3 — Auth & Session**
`authSlice` (Redux), `useAuth` hook (login/register/getMe via React Query mutations/query, dispatching session into Redux on success), `ProtectedRoute`, `/login` + `/register` pages, logout action.

**Phase 4 — Personal Access Tokens**
`/settings/tokens`: list/create/revoke, one-time raw-token reveal UI.

**Phase 5 — Workspace Management**
`/workspaces` list, `/workspaces/:id` detail via hierarchy endpoint, create/edit(PATCH)/delete workspace, add-member-by-email + member list.

**Phase 6 — Repository & Branch Management**
Two-step "add repository" (inspect-branches → create), render nested branches with `indexing_status` badges, delete repository/branch.

**Phase 7 — Sub-Project (SCIP Target) Configuration**
Create/delete sub-project under a branch (`root_dir` + `language` select).

**Phase 8 — Indexing Trigger & Status**
Workspace-level and branch-level reindex buttons, indexing-jobs panel with progress bar, polling via `refetchInterval` while jobs are in-flight.

**Phase 9 — Template Features**
Build every item from the "Missing-API Items" table: pages/forms/buttons wired to `*.template.ts` stub hooks only, visibly marked as not-yet-live.

**Phase 10 — Polish**
Loading/skeleton states via React Query status flags; shadcn `AlertDialog` replacing `window.confirm`; centralized toast handling via `uiSlice` + React Query global `onError`; remove dead code from the old `services/` layer once fully migrated; `tsc -b`/`npm run build` clean.

*(Phases 0–10 above: implemented and verified — see Status note at top of this document.)*

## Migration Plan — Round 2 (Backend API Update)

Straightforward path-and-type sync plus two capability swaps (one promotion, one demotion) and two adopted enhancements. No architectural changes — the `api/` → `hooks/` → UI separation and the envelope-unwrapping `http.ts` already absorb this without touching `pages/`/`components/` for most of it.

**Step A — Path & type sync (mechanical, no behavior change)**
- `src/api/types/workspace.ts`: rename `WorkspaceCreate` → `CreateWorkspaceRequest` (cosmetic); add `workspace_id?: number | null` and `full_name?: string | null` to `MemberResponse`; relax `AddMemberRequest` to `{email?: string; user_id?: number}` (keep the email-only form UI, just widen the type).
- `src/api/types/project.ts`: add `ProjectUpdateRequest { root_dir?: string; language?: SourceLanguage }`.
- `src/api/types/indexing.ts`: add `TriggerBranchIndexingRequest { commit_hashed?: string | null }`.
- `src/api/types/templates.ts` / `projects.template.ts`: delete the old ad-hoc `UpdateProjectRequest` template type/stub — superseded by the real `ProjectUpdateRequest`.
- Fix every path string in `repositories.api.ts`, `branches.api.ts`, `projects.api.ts`, `indexing.api.ts`, and the hierarchy call in `workspaces.api.ts` per the Folder Structure comments above (`/workspaces/{id}/...` → `/branches/{id}/...` or `/indexing/{id}/...`). `inspectGitHubBranchesApi` loses its `workspaceId` parameter entirely.
- Move `triggerBranchIndexApi` from `branches.api.ts` into `indexing.api.ts`, extend its signature to accept an optional `commit_hashed`.
- `tsc -b` should immediately surface every call site that needs updating (signature changes ripple through `hooks/` call sites) — use it as a checklist, not just a final gate.

**Step B — Promote to real: remove-member, update-project**
- `useWorkspaces.ts`: move `removeMemberApi` import from `workspaces.template.ts` to `workspaces.api.ts`; `useRemoveMemberMutation` now invalidates the hierarchy query on success like the other real workspace mutations.
- `MembersPanel.tsx`: drop the `TemplateBadge` next to the remove button; the existing `AlertDialog` confirm flow stays as-is (just starts working for real).
- `useProjects.ts`: move `updateProjectApi` import from `projects.template.ts` to `projects.api.ts`.
- `ProjectItem.tsx`: today `handleEdit` just resubmits the project's own unchanged values as a no-op template call — replace with a real "Edit sub-project" dialog (reuse `AddProjectDialog`'s form fields, pre-filled, submitting via `PATCH`) and drop its `TemplateBadge`.

**Step C — Demote to template: workspace update**
- `useWorkspaces.ts`: remove `useUpdateWorkspaceMutation` (real) and add `useUpdateWorkspaceMutation` sourced from a new `updateWorkspaceApi` stub in `workspaces.template.ts` instead (same hook name/shape so `OverviewPanel.tsx` needs minimal changes).
- `OverviewPanel.tsx`: add a `TemplateBadge` next to the rename/description form; everything else (the form itself, the delete-workspace flow, owner-only gating) stays as-is since delete is still real.

**Step D — Adopted enhancements**
- Branch reindex dialog (wherever `useTriggerBranchIndexMutation` is invoked in `BranchItem.tsx`): add an optional "Reindex tại commit cụ thể" text input feeding `commit_hashed` into the request; leave it blank by default (backend re-indexes at the branch's currently-registered commit).
- New "Branches" view: add `listWorkspaceBranchesApi` (`GET /branches/{workspaceId}/workspace-branches`, optional `repository_id` query) to `branches.api.ts`, a `useWorkspaceBranchesQuery` hook, and a new tab/section on `WorkspaceDetailPage.tsx` (or a filter control on the existing Repositories tab) listing branches flatly with a per-repository filter dropdown — reuses `IndexingStatusBadge` and the existing branch-reindex/delete actions rather than duplicating them.

**Step E — Re-verify**
Same checklist as the original Verification section below, plus explicitly re-testing: remove a member for real, edit a sub-project's `root_dir`/`language` for real, trigger a branch reindex with a commit override, browse the new Branches view, and confirm the workspace rename form now shows the template badge and a clear error toast instead of a fake success.

## Verification

- `npm run dev`, exercise end-to-end: register → login → create workspace → add member by email → **remove that member (real)** → inspect-branches on a real git URL → attach repository with selected branches → view hierarchy → configure a sub-project under a branch → **edit that sub-project's root_dir/language (real)** → **browse the new Branches view, filter by repository** → trigger workspace/branch reindex (**optionally with a commit override**) and watch job status/progress → create and revoke a PAT → delete a workspace (rename/description is template-only now).
- Exercise every template feature (including the now-template workspace rename) and confirm it's fully clickable/demoable end-to-end in the UI without throwing unhandled errors, while clearly not making a real network call.
- Confirm via browser network tab that every *live* call matches `openapi.json` exactly (method, path, payload field names, correct router — `/branches/*` vs `/indexing/*` vs `/workspaces/*`) and that no call is made to any excluded (`/mcp/v1/*`, `/api/v1/vector/*`) or template-only path.
- `npm run build` (`tsc -b && vite build`) passes with no type errors.
