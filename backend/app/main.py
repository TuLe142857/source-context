"""Main FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.postgres import Base, database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle including database connection and table creation.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    try:
        async with database.engine.begin() as conn:
            # Create all database tables (e.g. users) if they do not exist
            await conn.run_sync(Base.metadata.create_all)
        print("Database connected and schema initialized successfully.")
    except Exception as exc:
        print(f"Warning: Could not connect to Database at startup: {exc}")

    yield

    await database.engine.dispose()
    print("Database disconnected.")


app = FastAPI(
    title="Source Context API",
    description="Backend indexing, retrieval, and intelligence platform service.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router)
