"""Base abstract class for language sub-project extractors."""

from abc import ABC, abstractmethod
from pathlib import Path

from app.repository_manager_v2.profile_extractor.models import SubrepoProfileResult


class BaseSubprojectExtractor(ABC):
    """Abstract base extractor for language-specific subprojects."""

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """List of language identifiers supported by this extractor (e.g. ['python'])."""
        ...

    @abstractmethod
    def extract(
        self,
        local_dir: Path,
        name: str,
        root_dir: str,
        language: str | None = None,
    ) -> SubrepoProfileResult:
        """Extracts technical profile for the subproject from local disk.

        Args:
            local_dir (Path): Subproject root directory on local disk.
            name (str): Subproject name.
            root_dir (str): Relative root path in repository.
            language (str | None, optional): Explicit language configured by user.

        Returns:
            SubrepoProfileResult: Extracted sub-repository profile data.
        """
        ...
