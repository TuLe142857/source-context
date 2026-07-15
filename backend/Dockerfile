FROM python:3.13 AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS dev

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY ./pyproject.toml ./uv.lock ./
COPY ./backend/pyproject.toml /app/backend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-install-workspace

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/backend
CMD ["fastapi", "dev", "app/main.py", "--reload", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS builder

FROM builder as prod



