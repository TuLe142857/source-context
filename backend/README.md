# Source Context — Backend

> Indexing and retrieval service for the Source Context code intelligence platform.

The backend is a **FastAPI** application that prepares source repositories (local or public GitHub), scans them for supported source files, and exposes a REST API consumed by the MCP server and frontend.

---

## Table of Contents

- [Requirements](#requirements)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Repository Manager](#repository-manager)
- [Project Layout](#project-layout)
- [Testing](#testing)

---

## Requirements

| Tool | Version |
|------|---------|
| Python | `>=3.12, <3.13` |
| [uv](https://docs.astral.sh/uv/) | latest |
| Git | any recent version |

---

## Local Development

Install and synchronize all workspace dependencies from the **repository root**:

```bash
uv sync --all-packages
```

Start the development server with hot-reload:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify the server is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Source Context Backend",
  "version": "0.1.0",
  "environment": "development"
}
```

Interactive API documentation is available at:

| Interface | URL |
|-----------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Configuration

Settings are loaded from a `.env` file (or environment variables) using the `SOURCE_CONTEXT_` prefix.
Copy the example file from the repository root to get started:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_CONTEXT_APP_NAME` | `Source Context Backend` | Service name reported by the health endpoint |
| `SOURCE_CONTEXT_APP_VERSION` | `0.1.0` | Service version reported by the health endpoint |
| `SOURCE_CONTEXT_ENVIRONMENT` | `development` | Runtime environment (`development` \| `test` \| `production`) |
| `SOURCE_CONTEXT_DEBUG` | `false` | Enable FastAPI debug mode |
| `SOURCE_CONTEXT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL`) |
| `SOURCE_CONTEXT_API_V1_PREFIX` | `/api/v1` | Prefix applied to all versioned API routes |
| `SOURCE_CONTEXT_REPOSITORY_WORKSPACE_ROOT` | `workspace-repositories` | Directory where public GitHub repositories are cloned |
| `SOURCE_CONTEXT_SCANNER_MAX_FILE_SIZE_BYTES` | `1000000` | Files larger than this limit are skipped during scanning |
| `SOURCE_CONTEXT_GIT_COMMAND_TIMEOUT_SECONDS` | `120` | Maximum time (seconds) allowed for any Git subprocess |

---

## API Reference

### `GET /health`

Returns the current service status and build metadata.

**Response `200 OK`**

```json
{
  "status": "ok",
  "service": "Source Context Backend",
  "version": "0.1.0",
  "environment": "development"
}
```

**Error responses** use the common error schema:

```json
{
  "code": "error_code",
  "message": "Human-readable description of the error."
}
```

---

## Repository Manager

Repository Manager prepares source repositories for scanning. It supports two acquisition strategies:

| Strategy | Description |
|----------|-------------|
| **Local** | Uses an existing Git repository on the local filesystem |
| **GitHub Public** | Shallow-clones a public GitHub repository into the managed workspace |

### Managed Workspace

Public repositories are shallow-cloned into a configurable local directory:

```
workspace-repositories/
  github__tai0colaocacho__helicorp-macbook-pro-landing/
  github__tiangolo__fastapi/
  ...
```

The workspace root is controlled by `SOURCE_CONTEXT_REPOSITORY_WORKSPACE_ROOT`.

### CLI Script

A standalone script is provided for development and debugging:

**Scan a local Git repository** (any subdirectory works — the Git root is resolved automatically):

```bash
uv run python backend/scripts/scan_repository.py local "/path/to/your/project"
```

**Clone and scan a public GitHub repository:**

```bash
uv run python backend/scripts/scan_repository.py github "https://github.com/Tai0colaocacho/helicorp-macbook-pro-landing.git"
```

Both commands print a JSON snapshot to stdout:

```json
{
  "repository": { "name": "helicorp-macbook-pro-landing
", "owner": "Tai0colaocacho", "source_type": "github_public", ... },
  "git": { "branch": "main", "commit_sha": "abc123...", "remote_url": "..." },
  "statistics": { "included_file_count": 108, "ignored_file_count": 7, ... },
  "files": [
    { "relative_path": "...", "language": "javascript", "size_bytes": 12345, ... }
  ]
}
```

### Supported Languages

| Language | Extensions |
|----------|-----------|
| Python | `.py`, `.pyi` |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` |

Files that are **binary**, **oversized**, **symbolic links**, or matched by `.gitignore` are excluded automatically. Common directories such as `.git`, `node_modules`, `.venv`, and `__pycache__` are pruned before traversal.

---

## Project Layout

```
backend/
├── app/
│   ├── main.py                     # FastAPI application factory (create_app)
│   ├── api/
│   │   ├── router.py               # Top-level API router
│   │   ├── dependencies.py         # Shared FastAPI dependencies
│   │   └── routes/
│   │       └── health.py           # GET /health endpoint
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings, SOURCE_CONTEXT_ prefix)
│   │   ├── exceptions.py           # ApplicationError + JSON exception handler
│   │   └── logging.py              # Root logging configuration
│   ├── domain/
│   │   ├── repository.py           # Repository domain models & enums
│   │   └── source_file.py          # ScannedSourceFile + SourceLanguage
│   ├── repository_manager/
│   │   ├── service.py              # RepositoryManager orchestration
│   │   ├── clone.py                # GitHubPublicRepositoryProvider
│   │   ├── scanner.py              # RepositoryScanner (file discovery)
│   │   ├── git_client.py           # GitClient (subprocess wrapper)
│   │   ├── github_url.py           # GitHubUrlParser + GitHubRepositoryReference
│   │   ├── workspace.py            # RepositoryWorkspace (clone destinations)
│   │   ├── ignore_rules.py         # IgnoreRules (.gitignore + default prune list)
│   │   └── exceptions.py           # Repository-specific exceptions
│   └── schemas/
│       └── common.py               # HealthResponse, ErrorResponse
├── scripts/
│   └── scan_repository.py          # CLI: scan local or GitHub repository
├── tests/
│   ├── conftest.py                 # Shared fixtures (app factory, client, settings)
│   ├── unit/
│   │   ├── test_application_factory.py
│   │   ├── test_github_url.py
│   │   └── test_repository_workspace.py
│   └── integration/
│       ├── test_health_api.py
│       ├── test_exception_handler.py
│       ├── test_repository_scanner.py
│       └── test_repository_manager.py
├── Dockerfile
└── pyproject.toml
```

---

## Testing

Run the full test suite from the **repository root**:

```bash
uv run pytest
```

Run only backend tests:

```bash
uv run pytest backend/tests
```

Run tests by category using markers:

```bash
# Unit tests only
uv run pytest backend/tests/unit -m unit

# Integration tests only
uv run pytest backend/tests/integration -m integration
```

Run with coverage report:

```bash
uv run pytest --cov=app --cov-report=term-missing backend/tests
```