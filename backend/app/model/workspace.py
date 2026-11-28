"""SQLAlchemy ORM model for Workspace entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.branch import Branch
    from app.model.indexing_job import IndexingJob
    from app.model.member import Member
    from app.model.repository import Repository
    from app.model.user import User


class Workspace(Base):
    """Workspace database model representing a workspace."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workspace_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
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
        "Repository",
        secondary="workspace_repositories",
        back_populates="workspaces",
    )
    branches: Mapped[list["Branch"]] = relationship(
        "Branch",
        secondary="workspace_branches",
        back_populates="workspaces",
    )
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(
        "IndexingJob", back_populates="workspace", cascade="all, delete-orphan"
    )

    @property
    def name(self) -> str:
        """Alias property for backward compatibility with dbdiagram spec."""
        return self.workspace_name
