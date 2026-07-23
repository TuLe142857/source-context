"""Enumeration for member roles in a project."""

from enum import StrEnum


class MemberRole(StrEnum):
    """Roles for project members in a project."""

    ADMIN = "Admin"
    DEVELOPER = "Developer"
    VIEWER = "Viewer"
