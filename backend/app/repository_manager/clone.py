"""Preparation of managed public GitHub repositories."""

from app.domain.repository import (
    PreparedRepository,
    RepositoryAcquisitionStatus,
    RepositorySourceType,
)
from app.repository_manager.exceptions import (
    InvalidGitHubUrlError,
    RepositoryDestinationConflictError,
)
from app.repository_manager.git_client import GitClient
from app.repository_manager.github_url import GitHubUrlParser
from app.repository_manager.workspace import RepositoryWorkspace


class GitHubPublicRepositoryProvider:
    """Clone or reuse a managed public GitHub repository."""

    def __init__(
        self,
        *,
        url_parser: GitHubUrlParser,
        workspace: RepositoryWorkspace,
        git_client: GitClient,
    ) -> None:
        self._url_parser = url_parser
        self._workspace = workspace
        self._git_client = git_client

    def prepare(
        self,
        repository_url: str,
    ) -> PreparedRepository:
        """Prepare a public GitHub repository for scanning."""

        reference = self._url_parser.parse(
            repository_url,
        )

        destination = self._workspace.destination_for(
            reference,
        )

        if destination.exists():
            metadata = self._git_client.get_metadata(
                destination,
            )

            if metadata.remote_url is None:
                raise RepositoryDestinationConflictError(
                    destination,
                )

            try:
                existing_reference = self._url_parser.parse(
                    metadata.remote_url,
                )
            except InvalidGitHubUrlError as exc:
                raise RepositoryDestinationConflictError(
                    destination,
                ) from exc

            if (
                existing_reference.owner.casefold() != reference.owner.casefold()
                or existing_reference.repository.casefold() != reference.repository.casefold()
            ):
                raise RepositoryDestinationConflictError(
                    destination,
                )

            acquisition_status = RepositoryAcquisitionStatus.REUSED
        else:
            self._git_client.clone_public_repository(
                reference.clone_url,
                destination,
            )

            acquisition_status = RepositoryAcquisitionStatus.CLONED

        return PreparedRepository(
            repository_id=reference.repository_id,
            source_type=RepositorySourceType.GITHUB_PUBLIC,
            acquisition_status=acquisition_status,
            name=reference.repository,
            owner=reference.owner,
            local_path=destination,
            remote_url=reference.clone_url,
        )
