"""SQLAlchemy ORM model for Workspace entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.member import Member
    from app.model.repository import Repository
    from app.model.user import User


class Workspace(Base):
    """Workspace database model representing a workspace."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_workspaces")
    members: Mapped[list["Member"]] = relationship(
        "Member", back_populates="workspace", cascade="all, delete-orphan"
    )
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository", back_populates="workspace", cascade="all, delete-orphan"
    )
