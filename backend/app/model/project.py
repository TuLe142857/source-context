"""SQLAlchemy ORM model for Project entity."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base
from app.domain.source_file import SourceLanguage

if TYPE_CHECKING:
    from app.model.branch import Branch
    from app.model.subrepo_profile import SubrepoProfile


class Project(Base):
    """Project database model representing a project root directory and language on a branch."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        default=None,
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_dir: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[SourceLanguage] = mapped_column(
        SQLEnum(SourceLanguage, name="language_enum", native_enum=False),
        nullable=False,
    )

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch", back_populates="projects")
    subrepo_profile: Mapped["SubrepoProfile | None"] = relationship(
        "SubrepoProfile",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def langguage(self) -> SourceLanguage:
        """Alias for language field matching dbdiagram spec."""
        return self.language
