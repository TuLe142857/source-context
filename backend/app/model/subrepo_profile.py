"""SQLAlchemy ORM model for SubrepoProfile entity."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.project import Project
    from app.model.repo_profile import RepoProfile


class SubrepoProfile(Base):
    """Sub-repository (project) technical profile model containing tech stack, frameworks, and entrypoints."""

    __tablename__ = "subrepo_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_profile_id: Mapped[int] = mapped_column(
        ForeignKey("repo_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_dir: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )
    project_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )

    frameworks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    tech_stack: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    key_entrypoints: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    directory_map: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    extra_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    repo_profile: Mapped["RepoProfile"] = relationship(
        "RepoProfile", back_populates="subrepo_profiles"
    )
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="subrepo_profile"
    )
