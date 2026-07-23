"""SQLAlchemy ORM model for User entity."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.domain.member import Member
    from app.domain.pat import PersonalAccessToken
    from app.domain.project import Project


class User(Base):
    """User database model representing application users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    owned_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list["Member"]] = relationship(
        "Member", back_populates="user", cascade="all, delete-orphan"
    )
    personal_access_tokens: Mapped[list["PersonalAccessToken"]] = relationship(
        "PersonalAccessToken", back_populates="user", cascade="all, delete-orphan"
    )
