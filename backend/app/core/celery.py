"""Celery configuration module for asynchronous background task queue."""

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

app_settings = get_settings()

celery_app = Celery(
    "source_context_tasks",
    broker=app_settings.CELERY_BROKER_URL,
    backend=app_settings.CELERY_BROKER_URL,
    include=["app.indexing.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
