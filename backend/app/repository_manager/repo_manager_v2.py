"""Backward compatibility re-exports for Repository Manager V2.

This module re-exports components now housed in `app.repository_manager_v2`.
"""

from app.repository_manager_v2.manager import (
    RepoManagerV2,
    RepositoryManagerV2,
    clone_private_repo,
    download_repo_tarball,
    get_installation_token,
    get_repo_details,
    list_authorized_repos,
    post_download_metadata_hook,
)

__all__ = [
    "RepoManagerV2",
    "RepositoryManagerV2",
    "clone_private_repo",
    "download_repo_tarball",
    "get_installation_token",
    "get_repo_details",
    "list_authorized_repos",
    "post_download_metadata_hook",
]
