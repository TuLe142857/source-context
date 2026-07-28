# Development Guide

# Tech Stack & Project Structure
## TechStack
Coming soon :)
## Project Structure
Coming soon :)


# Build & Run

## Backend, Frontend

```shell

git clone https://github.com/TuLe142857/source-context.git
cd source-context
cp .env.example .env.dev
make dev-build
# Or manually:
# docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

These are the default configurations. You can modify them by editing your .env file.
- Backend API: http://localhost:8000
- Backend Swagger UI: 
  - http://localhost:8000/docs
  - http://localhost:8000/redoc
- Frontend: http://localhost:5173
- Postgres:
  - port: 5432
- Neo4j:
  - Driver port: 7687
  - Web UI: http://localhost:7474
- Qdrant:
  - gRPC port: 6334
  - WebUI: http://127.0.0.1:6333/dashboard
- Redis:
  - port: 6379
  - RedisInsight(Web UI for redis): http://localhost:5540
- MinIO:
  - API port: 9000
  - WebUI: http://localhost:9001
- MailHog(Fake mail server for development):
  - SMTP port: 1025
  - Web UI: http://localhost:8025

## MCP
Build and install locally (use `--editable` for hot reload during development):  
```shell
cd mcp
uv build
uv tool install . --editable
```

Coding Agent Configurations:  
**Antigravity:**  
- Config path:
  - Global: `~/.gemini/config/mcp_config.json`
  - Workspace: `.agents/mcp_config.json`
- Config:
    ```json
    {
      "mcpServers": {
        "source-context": {
          "command": "uvx",
          "args": [
            "source-context-mcp"
          ]
        }
      }
    }
    ```

**Claude code:**  
Coming soon :)

**Codex:**  
Coming soon :)

**Cursor:**  
Coming soon :)

# Dependency Management

This project uses a `uv` workspace to manage dependencies. To add new libraries to specific workspace members (`backend` or `mcp`), use the `--project` flag:

```shell
# Add a package to the backend
uv add <package_name> --project backend

# Add a package to the mcp
uv add <package_name> --project mcp
```

To add a development dependency (like a formatting or testing tool) for the entire workspace:
```shell
uv add <package_name> --dev
```

### Syncing with Docker
Because `pyproject.toml` and `uv.lock` are directly mounted into the `backend` container in development, you do **not** need to rebuild the Docker image after adding new packages locally.

Instead, simply run `uv sync` inside the running container to update its environment instantly:
```shell
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml exec -it backend uv sync
```
*(If the backend server doesn't hot-reload the new library automatically, you can restart it with `docker compose restart backend`)*

# Coding Rule
## Pre-commit:
This project uses [pre-commit](https://pre-commit.com/) to automatically run formatting, linting, and type-checking 
on every commit. It runs the configured hooks (ruff, mypy, etc.) on the staged files before the commit is created, 
and blocks the commit if any hook fails or modifies files — this keeps bad or unformatted code from entering the 
repository. Hooks are defined in `.pre-commit-config.yaml` at the repo root, so every contributor runs the exact same 
checks.

Install pre-commit hook after clone this repo(once):  
```shell
cd source-context
uv run pre-commit install
```

Run all hooks (format, lint, type check) manually without committing:  
```shell
uv run pre-commit run --all-files
```

Skip pre-commit hooks when necessary:  
```shell
git commit --no-verify
```

## Ruff:
Note: pre-commit has config to run ruff format and check.
Ruff is tool to format and lint Python code

To ignore linter: use `# noqa` or `# noqa <rule_code>` beside your code.

Format code:
```shell
# Check 
uv run ruff format --check

# Do format
uv run ruff format 
```

Lint:
```shell
# Check
uv run ruff check

# Check and show statistics(líst of rule + count)
uv run ruff check --statistics

# Fix
uv run ruff check --fix
```

## mypy
Type checker for Python
Always use typehint when code python

```shell
uv run mypy .
```

To ignore mypy check in your code, add `# type: ignore`: 
```python
def say_hi(): # type: ignore
  return None

```

## ESLint
Code lint for js
Coming soon :)

## Prettier
Code formater for js
Coming soon :)