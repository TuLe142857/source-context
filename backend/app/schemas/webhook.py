"""Pydantic schemas for GitHub App Webhooks and Installation status."""

from pydantic import BaseModel


class GitHubStatusResponse(BaseModel):
    """Schema representing current user's GitHub App connection status."""

    is_connected: bool
    github_installation_id: int | None = None
    github_username: str | None = None
    manage_url: str | None = None


class GitHubWebhookResponse(BaseModel):
    """Schema for generic webhook response payload."""

    status: str
    message: str | None = None
    reason: str | None = None
    branches_updated_to_outdated: int | None = None
    repositories_tracked: int | None = None
