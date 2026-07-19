"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance."""

    app_settings = settings if settings is not None else get_settings()

    configure_logging(app_settings.log_level)

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=("Source code indexing and retrieval API for the Source Context MCP platform."),
        debug=app_settings.debug,
    )

    application.state.settings = app_settings

    register_exception_handlers(application)
    application.include_router(api_router)

    logger.info(
        "Backend application configured: environment=%s",
        app_settings.environment,
    )

    return application


app = create_app()
