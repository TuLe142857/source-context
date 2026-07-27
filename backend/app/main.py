"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.postgres import Base, database

from .worker import create_worker

celery_worker = create_worker()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle including database connection and table creation."""
    try:
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connected and schema initialized successfully.")
    except Exception as exc:
        logger.warning("Could not connect to Database at startup: %s", exc)

    yield

    await database.engine.dispose()
    logger.info("Database disconnected.")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app_settings = settings if settings is not None else get_settings()

    configure_logging(app_settings.log_level)

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Source code indexing and retrieval API for the Source Context MCP platform.",
        debug=app_settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.state.settings = app_settings

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)

    logger.info(
        "Backend application configured: environment=%s", app_settings.environment
    )

    return application


app = create_app()
