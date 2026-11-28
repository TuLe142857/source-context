"""SQLAlchemy ORM model for WorkspaceRepository association entity."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WorkspaceRepository(Base):
    """Association database model linking Workspaces and Repositories (Many-to-Many)."""

    __tablename__ = "workspace_repositories"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True
    )
