from celery import Celery
from app.core.config import get_settings


def create_worker():
    """
    Create the celery worker and set this worker to default
    Returns:

    """
    settings = get_settings()
    worker = Celery(
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_BROKER_URL,
        include=["app.tasks"],
    )
    worker.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
    )
    worker.set_default()
    return worker


celery_worker = create_worker()
