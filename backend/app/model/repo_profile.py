"""SQLAlchemy ORM model for RepoProfile entity."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.branch import Branch
    from app.model.repository import Repository


class RepoProfile(Base):
    """Repository technical profile model containing tech stack, conventions, and architectural metadata."""

    __tablename__ = "repo_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    branch_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="main"
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)

    primary_language: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )
    project_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB columns storing structured profile metadata
    tech_stack: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    dev_commands: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    coding_conventions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    key_entrypoints: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    directory_map: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    extra_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="profile"
    )
    branch: Mapped["Branch | None"] = relationship("Branch")
