"""Domain models representing managed source repositories."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, ConfigDict

from app.domain.source_file import ScannedSourceFile


class RepositorySourceType(StrEnum):
    """Supported origins of source repositories."""

    LOCAL = "local"
    GITHUB_PUBLIC = "github_public"


class RepositoryAcquisitionStatus(StrEnum):
    """How a local repository workspace was obtained."""

    LOCAL = "local"
    CLONED = "cloned"
    REUSED = "reused"


@dataclass(frozen=True, slots=True)
class PreparedRepository:
    """A repository that is ready to be inspected and scanned."""

    repository_id: str
    source_type: RepositorySourceType
    acquisition_status: RepositoryAcquisitionStatus
    name: str
    owner: str | None
    local_path: Path
    remote_url: str | None


@dataclass(frozen=True, slots=True)
class GitRepositoryMetadata:
    """Git metadata for one repository snapshot."""

    repository_root: Path
    branch: str | None
    commit_sha: str
    remote_url: str | None


@dataclass(frozen=True, slots=True)
class RepositoryScanStatistics:
    """Statistics collected while scanning repository files."""

    discovered_file_count: int
    included_file_count: int
    ignored_file_count: int
    pruned_directory_count: int
    unsupported_file_count: int
    oversized_file_count: int
    binary_file_count: int
    symlink_file_count: int
    inaccessible_file_count: int


@dataclass(frozen=True, slots=True)
class RepositoryScanResult:
    """Source-file scan result before Git metadata is attached."""

    repository_root: Path
    files: tuple[ScannedSourceFile, ...]
    statistics: RepositoryScanStatistics


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """Immutable snapshot returned by the Repository Manager."""

    repository: PreparedRepository
    git: GitRepositoryMetadata
    files: tuple[ScannedSourceFile, ...]
    statistics: RepositoryScanStatistics


# Pydantic schemas for ORM Repository endpoints (attaching repository links to projects)


class RepositoryLinkCreate(BaseModel):
    """Schema for attaching a Git repository link to a project."""

    name: str
    git_url: str
    description: str | None = None
    default_branch: str = "main"


class RepositoryLinkResponse(BaseModel):
    """Schema for returning attached Git repository link information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    git_url: str
    description: str | None
    default_branch: str
    status: str
    created_at: datetime
    updated_at: datetime
