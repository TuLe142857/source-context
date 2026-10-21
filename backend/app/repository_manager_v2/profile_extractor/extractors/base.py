"""Base language profile extractor interface.

Defines the strategy interface that every language-specific extractor must implement.
"""

from abc import ABC, abstractmethod

from app.repository_manager_v2.profile_extractor.models import RepoProfileResult
from app.repository_manager_v2.profile_extractor.providers.base import (
    SourceFileProvider,
)


class BaseLanguageExtractor(ABC):
    """Abstract Strategy interface for language-specific profile extractors."""

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Primary programming language name handled by this extractor."""
        ...

    @abstractmethod
    def can_handle(self, provider: SourceFileProvider) -> bool:
        """Determines if the repository contains markers/manifests for this language.

        Args:
            provider (SourceFileProvider): File inspection provider.

        Returns:
            bool: True if this extractor can profile the repository.
        """
        ...

    @abstractmethod
    def extract(self, provider: SourceFileProvider) -> RepoProfileResult:
        """Extracts technical profile, dependencies, and configuration.

        Args:
            provider (SourceFileProvider): File inspection provider.

        Returns:
            RepoProfileResult: Extracted language-specific profile.
        """
        ...
