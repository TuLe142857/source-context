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
    from app.model.subrepo_profile import SubrepoProfile


class RepoProfile(Base):
    """Repository-level profile containing high-level metadata, summary, and sub-project profiles."""

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
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    readme_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    topics: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    languages_breakdown: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
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
    subrepo_profiles: Mapped[list["SubrepoProfile"]] = relationship(
        "SubrepoProfile",
        back_populates="repo_profile",
        cascade="all, delete-orphan",
        order_by="SubrepoProfile.id",
    )
