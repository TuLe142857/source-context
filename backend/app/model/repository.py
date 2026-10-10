"""SQLAlchemy ORM model for Repository entity."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.branch import Branch
    from app.model.workspace import Workspace


class Repository(Base):
    """Repository database model representing a repository shared across workspaces."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    git_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    github_repository_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )

    # Relationships
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        secondary="workspace_repositories",
        back_populates="repositories",
    )
    branches: Mapped[list["Branch"]] = relationship(
        "Branch", back_populates="repository", cascade="all, delete-orphan"
    )
