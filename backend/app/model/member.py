"""SQLAlchemy ORM model for Member entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.postgres import Base

if TYPE_CHECKING:
    from app.model.user import User
    from app.model.workspace import Workspace


class Member(Base):
    """Member database model representing user membership in a workspace."""

    __tablename__ = "members"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")
