"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from app.api.routes import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.postgres import Base, database
from app.core.s3 import get_s3_client, create_default_bucket_if_not_exists
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from .worker import create_worker

celery_worker = create_worker()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle including database connection and table creation."""

    settings = get_settings()

    # POSTGRES
    try:
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connected and schema initialized successfully.")
    except Exception as exc:
        logger.warning("Could not connect to Database at startup: %s", exc)

    # NEO4J
    try:
        async with AsyncGraphDatabase.driver(
            f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
        ) as driver:
            await driver.verify_connectivity()
            logger.info("Neo4j connect successfully.")
    except Neo4jError as exc:
        logger.warning("Could not connect to Neo4j: %s", exc)

    # S3
    s3_client = get_s3_client()
    try:
        await run_in_threadpool(s3_client.list_buckets)
        logger.info("S3 client connected successfully.")

        await run_in_threadpool(create_default_bucket_if_not_exists, s3_client)
        logger.info(
            f"S3 client create default bucket {settings.S3_DEFAULT_BUCKET} successfully."
        )
    except (
        s3_client.exceptions.BucketAlreadyExists,
        s3_client.exceptions.BucketAlreadyOwnedByYou,
    ):
        logger.info("Bucket Already Exists. No need to create")

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
