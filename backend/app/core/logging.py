"""Logging configuration for the backend application."""

import logging

from app.core.config import LogLevel

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: LogLevel) -> None:
    """Configure root application logging."""

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
    )

    logging.getLogger().setLevel(level)
