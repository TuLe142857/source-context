"""SQLAlchemy ORM model for Branch entity."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base
from app.enums import BranchIndexingStatus

if TYPE_CHECKING:
    from app.model.indexing_job import IndexingJob
    from app.model.project import Project
    from app.model.repository import Repository
    from app.model.workspace import Workspace


class Branch(Base):
    """Branch database model representing a repository branch."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_hashed: Mapped[str] = mapped_column(
        String(255), nullable=False, default="HEAD"
    )
    indexing_status: Mapped[BranchIndexingStatus] = mapped_column(
        SQLEnum(
            BranchIndexingStatus,
            name="branch_indexing_status_enum",
            native_enum=False,
        ),
        nullable=False,
        default=BranchIndexingStatus.UNINDEXED,
    )

    local_path: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="branches"
    )
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        secondary="workspace_branches",
        back_populates="branches",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="branch", cascade="all, delete-orphan"
    )
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(
        "IndexingJob", back_populates="branch", cascade="all, delete-orphan"
    )
