FROM python:3.13 AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS dev

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY ./pyproject.toml ./uv.lock ./
COPY ./backend/pyproject.toml /app/backend/
COPY ./mcp/pyproject.toml /app/mcp/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --package source-context-backend

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/backend
CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY ./pyproject.toml ./uv.lock ./
COPY ./backend/pyproject.toml /app/backend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-install-workspace --no-dev

FROM base AS prod

WORKDIR /app
COPY backend/app /app/backend/app
COPY --from=builder /app/.venv /app/.venv/
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]