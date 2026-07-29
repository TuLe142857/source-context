"""SQLAlchemy ORM model for WorkspaceBranch association entity."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.postgres import Base


class WorkspaceBranch(Base):
    """Association database model linking Workspaces and Branches (Many-to-Many)."""

    __tablename__ = "workspace_branches"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True
    )
