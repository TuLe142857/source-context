"""Tests for public GitHub repository URL parsing."""

import pytest

from app.repository_manager.exceptions import (
    InvalidGitHubUrlError,
)
from app.repository_manager.github_url import GitHubUrlParser


@pytest.mark.parametrize(
    ("repository_url", "owner", "repository"),
    [
        (
            "https://github.com/encode/httpx",
            "encode",
            "httpx",
        ),
        (
            "https://github.com/encode/httpx.git",
            "encode",
            "httpx",
        ),
        (
            "https://www.github.com/owner/project-name",
            "owner",
            "project-name",
        ),
    ],
)
def test_parser_accepts_supported_github_urls(
    repository_url: str,
    owner: str,
    repository: str,
) -> None:
    """Supported GitHub URLs should be normalized."""

    reference = GitHubUrlParser.parse(
        repository_url,
    )

    assert reference.owner == owner
    assert reference.repository == repository
    assert reference.clone_url == (f"https://github.com/{owner}/{repository}.git")


@pytest.mark.parametrize(
    "repository_url",
    [
        "http://github.com/owner/repository",
        "https://gitlab.com/owner/repository",
        "git@github.com:owner/repository.git",
        "https://github.com/owner",
        "https://github.com/owner/repository/issues",
        "https://github.com/owner/repository?tab=readme",
        "https://github.com/../repository",
        "https://github.com/./repository",
        "https://github.com/owner/..",
        "https://github.com/%2e%2e/repository",
        "https://github.com/owner/%2e%2e",
    ],
)
def test_parser_rejects_unsupported_urls(
    repository_url: str,
) -> None:
    """Unsupported repository URLs should be rejected."""

    with pytest.raises(InvalidGitHubUrlError):
        GitHubUrlParser.parse(repository_url)
