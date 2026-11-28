"""Declarative base and schema initialization for all SQLAlchemy ORM models."""

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


async def init_db(engine: AsyncEngine) -> None:
    """Creates all ORM tables that do not exist yet.

    Imports the ``app.model`` package first so every model is registered on
    ``Base.metadata``, whichever entrypoint calls this function.

    Args:
        engine (AsyncEngine): Engine bound to the target database.
    """
    import app.model  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
