"""Database connection and session management module using async SQLAlchemy."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


class Database:
    """Async Database singleton class managing engine and session lifecycle."""

    _instance: "Database | None" = None
    engine: AsyncEngine
    async_session_factory: async_sessionmaker[AsyncSession]

    def __new__(cls) -> "Database":
        """Creates or returns singleton Database instance.

        Returns:
            Database: The singleton database instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.engine = create_async_engine(
                settings.ASYNC_DATABASE_URL,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )
            cls._instance.async_session_factory = async_sessionmaker(
                bind=cls._instance.engine,
                class_=AsyncSession,
                autoflush=False,
                expire_on_commit=False,
            )
        return cls._instance


database = Database()
