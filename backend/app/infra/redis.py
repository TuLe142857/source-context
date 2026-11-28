"""Redis client singleton factory."""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings


@lru_cache
def get_redis_async_client() -> Redis:
    """
    Get Redis async client.
    Returns:
        Redis AsyncClient instance.
    """
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        username=settings.REDIS_USER or None,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
