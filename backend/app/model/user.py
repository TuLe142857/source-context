"""SQLAlchemy ORM model for User entity."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.member import Member
    from app.model.pat import PAT
    from app.model.workspace import Workspace


class User(Base):
    """User database model representing application users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    is_active: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    owned_workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="owner", cascade="all, delete-orphan"
    )
    workspace_memberships: Mapped[list["Member"]] = relationship(
        "Member", back_populates="user", cascade="all, delete-orphan"
    )
    pats: Mapped[list["PAT"]] = relationship(
        "PAT", back_populates="user", cascade="all, delete-orphan"
    )
