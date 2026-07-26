"""SQLAlchemy ORM model for Branch entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.project import Project
    from app.model.repository import Repository


class Branch(Base):
    """Branch database model representing a repository branch."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_hashed: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="branches"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="branch", cascade="all, delete-orphan"
    )
