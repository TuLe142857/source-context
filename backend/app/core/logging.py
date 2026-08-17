"""Logging configuration for the backend application."""

import logging
import json
import sys
from typing import Literal

from app.core.config import LogLevel

from .config import get_settings


class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger_name": record.name,
            "module": f"{record.module}:{record.lineno}",
            "thread_id": record.thread,
            "thread_name": record.threadName,
            "msg": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(
    level: LogLevel | None = None, fmt: Literal["plain", "json"] | None = None
) -> None:
    """
    Configure logging for the backend application.
    Args:
        level: DEBUG | INFO | WARNING | ERROR | CRITICAL
        fmt: json | plain

    Returns:

    """
    settings = get_settings()
    if level is None:
        level = settings.log_level
    if fmt is None:
        fmt = settings.log_format

    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JSONLogFormatter())
    elif fmt == "plain":
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    loggers_override = ["uvicorn", "uvicorn.access", "uvicorn.error", "celery", "neo4j"]
    for logger_name in loggers_override:
        logger = logging.getLogger(logger_name)

        logger.handlers.clear()
        logger.addHandler(handler)

        logger.setLevel(level)

    # set neo4j logger to level error
    logging.getLogger("neo4j").setLevel(logging.ERROR)
