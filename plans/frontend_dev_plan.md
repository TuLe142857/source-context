# Frontend Development Plan — Source Context

## Context

Backend (`openapi.json`, source of truth) models a **Workspace → Repository → Branch → Project (sub-project/SCIP target)** hierarchy plus account/token management. The current frontend (`frontend/src/`) only implements a shell built around a concept it calls "Project" — but that concept actually corresponds to the backend's **Workspace**. Backend's real "Project" (a `root_dir` + `language` SCIP target nested under a Branch) doesn't exist in the frontend at all, and Repository/Branch aren't modeled as separate entities either.

Scope for this plan: **account management, workspace, and workspace configuration (repository, branch, sub-project)**. MCP endpoints, graph browsing, and vector/semantic search are explicitly **out of scope** (candidate for a later, separate plan). Indexing trigger/status (workspace/branch level) is **in scope**.

The backend does not yet use a unified response envelope on its REST surface (only the `/mcp/v1/*` routes currently wrap responses in `ResponseSuccessSchema`/`ResponseErrorSchema`), but `backend/app/core/response.py` + `backend/app/core/error_code.py` define the target shape it will migrate to. The frontend's API layer is designed now so that migration is a one-file change later, not a rewrite.

Goal: fix the terminology mismatch, build a clean API/UI-separated architecture, cover the full account/workspace/repository/branch/project configuration surface, and provide clearly-marked UI templates (with stub API hooks) for functionality the product will obviously need but the backend doesn't expose yet.

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
| Workspaces | `/api/v1/workspaces/*` | **Yes** — core. |
| Workspace Repositories & Hierarchy | `/api/v1/workspaces/{id}/repositories`, `/branches`, `/projects`, `/hierarchy`, `/index`, `/indexing-jobs` | **Yes** — core. |
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

## Known Backend Spec Quirks / Gaps (verified directly against `openapi.json`)

- `UserResponse.is_active` is typed as **string**, not boolean.
- Workspace update is **PATCH**, not PUT.
- No DELETE endpoint for workspace members, and no self-service "leave workspace".
- No endpoint to add a branch to an **already-existing** repository — branches are only registered together with the repo at creation time (`RepositoryCreateRequest.branches`).
- No update (PATCH/PUT) endpoint for Repository, Branch, or Project — create + delete only.
- Indexing can only be triggered at **workspace** level (`POST /workspaces/{id}/index`) or **branch** level (`POST /workspaces/{id}/branches/{id}/index`) — there is no project-level reindex endpoint.
- `GET /workspaces` pagination is `skip`/`limit` query params only, returning a plain array — no total-count metadata, so a page-number UI isn't possible until the backend adopts `ApiPaginationResponse`.
- No change-password, forgot-password, or update-own-profile endpoints exist at all.
- Collection endpoints exist in both trailing/no-trailing-slash form — use the no-trailing-slash form consistently.
- `IndexingJobResponse.status` is a free string, not formally tied to the `BranchIndexingStatus` enum.

## Missing-API Items → Build as UI Template + Stub Hook (per product decision)

These are **not** wired to any real endpoint. Each gets a real UI (form/button/page) and a stub API function + React Query hook living in a clearly separated `*.template.ts` file, so swapping in the real call later is a one-line import change. UI must visibly indicate these aren't live yet (e.g. a small "coming soon" badge or disabled+tooltip state is acceptable, but the flow itself should be fully clickable/demoable).

| Feature | Template location | Notes |
|---|---|---|
| Update Repository (rename), Update Branch (re-point `commit_hashed`), Update Project (`root_dir`/`language`) | `src/api/repositories.template.ts`, `branches.template.ts`, `projects.template.ts` | Edit forms reuse the same fields as the create forms. |
| Add branch to an existing repository | `src/api/repositories.template.ts` | Separate from the real "attach repository" 2-step flow. |
| Reindex a single Project (sub-project) | `src/api/projects.template.ts` | Per decision: kept as its own template action, distinct from the real branch/workspace-level reindex buttons (which call real endpoints). |
| Change password, forgot/reset password, edit own profile (username/full_name/email) | `src/api/account.template.ts` | Pages: `/settings/security`, `/forgot-password`, `/reset-password`, `/settings/profile`. |
| Leave workspace (self), remove a member (owner action) | `src/api/workspaces.template.ts` | Separate from the real "add member by email" flow, which is live. |

## Pages & Features

**Live (real API):**
1. `/login`, `/register` — auth forms.
2. Logout — action only (clears Redux session + axios auth header), no dedicated page.
3. `/settings/tokens` — Personal Access Tokens: list, create (show `raw_token` once, copy button, warning), revoke.
4. `/workspaces` — list of own/member workspaces (`GET /workspaces`), create-workspace modal.
5. `/workspaces/:workspaceId` — detail, built from `GET /workspaces/{id}/hierarchy`:
   - Overview: rename/description (`PATCH`), delete workspace (owner-only).
   - Members: list + add-by-email.
   - Repositories: list, each showing nested branches → nested sub-projects; "Add repository" 2-step flow (inspect-branches → create with selected branches); delete repository/branch/project; create sub-project (root_dir + language) under a branch.
   - Indexing: trigger workspace-level or per-branch reindex; indexing-jobs panel with live status/progress (polling while any job is in-flight).

**Template-only (UI + stub hook, no live API):**
6. `/settings/profile` — edit profile.
7. `/settings/security` — change password.
8. `/forgot-password`, `/reset-password` — password recovery flow.
9. Workspace detail → member row "Remove" action + "Leave workspace" button.
10. Repository/Branch/Project rows → "Edit" action.
11. Repository detail → "Add branch to existing repository" action.
12. Sub-project row → "Reindex this project" button.

## Folder Structure

```
src/
├── api/
│   ├── http.ts                     # axios instance + request/response interceptors (auth header, envelope unwrap, ApiError normalization, 401 handling)
│   ├── types/
│   │   ├── common.ts                # ApiResponse<T>, ApiPaginationResponse<T>, PaginationMeta, ErrorCode, ApiError
│   │   ├── auth.ts                  # UserResponse, TokenResponse
│   │   ├── tokens.ts                # PATResponse, PATCreateRequest, PATCreateResponse
│   │   ├── workspace.ts             # WorkspaceResponse, WorkspaceCreate, WorkspaceUpdate, WorkspaceHierarchyResponse, MemberResponse, AddMemberRequest
│   │   ├── repository.ts            # RepositoryResponse, RepositoryCreateRequest, RemoteBranchesResponse, InspectGitHubBranchesRequest
│   │   ├── branch.ts                # BranchResponse, BranchCreateRequest, BranchIndexingStatus
│   │   ├── project.ts               # ProjectResponse, ProjectCreateRequest, SourceLanguage
│   │   └── indexing.ts              # IndexingJobResponse
│   ├── auth.api.ts                  # login, register, getMe — real
│   ├── tokens.api.ts                # PAT CRUD — real
│   ├── workspaces.api.ts            # workspace CRUD + members(add/list) + hierarchy — real
│   ├── workspaces.template.ts       # removeMember, leaveWorkspace — stub
│   ├── repositories.api.ts          # inspect-branches, create, delete — real
│   ├── repositories.template.ts     # updateRepository, addBranchToRepository — stub
│   ├── branches.api.ts              # delete, trigger index — real
│   ├── branches.template.ts         # updateBranch — stub
│   ├── projects.api.ts              # create, delete sub-project — real
│   ├── projects.template.ts         # updateProject, reindexProject — stub
│   ├── indexing.api.ts              # trigger workspace index, list jobs — real
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

## Verification

- `npm run dev`, exercise end-to-end: register → login → create workspace → add member by email → inspect-branches on a real git URL → attach repository with selected branches → view hierarchy → configure a sub-project under a branch → trigger workspace/branch reindex and watch job status/progress → create and revoke a PAT → edit and delete a workspace.
- Exercise every template feature and confirm it's fully clickable/demoable end-to-end in the UI without throwing unhandled errors, while clearly not making a real network call.
- Confirm via browser network tab that every *live* call matches `openapi.json` exactly (method, path, payload field names) and that no call is made to any excluded (`/mcp/v1/*`, `/api/v1/vector/*`) or template-only path.
- `npm run build` (`tsc -b && vite build`) passes with no type errors.
