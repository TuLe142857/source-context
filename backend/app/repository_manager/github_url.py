"""Parsing and validation for GitHub repository URLs."""

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from app.github_app import github_app_client
from app.repository_manager.exceptions import InvalidGitHubUrlError

GITHUB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def is_valid_github_name(value: str) -> bool:
    """Return whether a GitHub owner or repository name is safe."""

    if value in {".", ".."}:
        return False

    return GITHUB_NAME_PATTERN.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class GitHubRepositoryReference:
    """Normalized reference to one GitHub repository."""

    owner: str
    repository: str

    @property
    def clone_url(self) -> str:
        """Return the normalized HTTPS clone URL."""

        return f"https://github.com/{self.owner}/{self.repository}.git"

    @property
    def repository_id(self) -> str:
        """Return a deterministic repository identifier."""

        return f"github__{self.owner.casefold()}__{self.repository.casefold()}"

    @property
    def workspace_directory_name(self) -> str:
        """Return the managed workspace directory name."""

        return self.repository_id


class GitHubUrlParser:
    """Validate and normalize GitHub HTTPS repository URLs."""

    @staticmethod
    def parse(repository_url: str) -> GitHubRepositoryReference:
        """Parse a supported GitHub repository URL."""

        parsed_url = urlparse(repository_url.strip())

        if parsed_url.scheme.lower() != "https":
            raise InvalidGitHubUrlError(repository_url)

        if parsed_url.hostname is None:
            raise InvalidGitHubUrlError(repository_url)

        if parsed_url.hostname.lower() not in {
            "github.com",
            "www.github.com",
        }:
            raise InvalidGitHubUrlError(repository_url)

        if parsed_url.username or parsed_url.password or parsed_url.port:
            raise InvalidGitHubUrlError(repository_url)

        if parsed_url.query or parsed_url.fragment:
            raise InvalidGitHubUrlError(repository_url)

        path_parts = [
            unquote(part) for part in parsed_url.path.strip("/").split("/") if part
        ]

        if len(path_parts) != 2:
            raise InvalidGitHubUrlError(repository_url)

        owner, repository = path_parts

        if repository.lower().endswith(".git"):
            repository = repository[:-4]

        if not is_valid_github_name(owner):
            raise InvalidGitHubUrlError(repository_url)

        if not is_valid_github_name(repository):
            raise InvalidGitHubUrlError(repository_url)

        return GitHubRepositoryReference(
            owner=owner,
            repository=repository,
        )


def fetch_github_branches(
    owner: str,
    repository: str,
    *,
    installation_id: int | None = None,
) -> list[str]:
    """Fetch remote branch names through GitHub's API.

    Args:
        owner: GitHub owner/organization name.
        repository: GitHub repository name.

    Returns:
        list[str]: List of branch names.
    """
    return github_app_client.list_branches(
        owner,
        repository,
        installation_id=installation_id,
    )
