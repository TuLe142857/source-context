"""Extractor registry managing available language profile extractors.

Implements the Registry Pattern to decouple extractor discovery from execution.
"""

from collections.abc import Sequence
from functools import lru_cache

from app.repository_manager_v2.profile_extractor.extractors.base import (
    BaseLanguageExtractor,
)
from app.repository_manager_v2.profile_extractor.extractors.python import (
    PythonProfileExtractor,
)
from app.repository_manager_v2.profile_extractor.providers.base import (
    SourceFileProvider,
)


class ExtractorRegistry:
    """Registry maintaining active language extractors."""

    def __init__(
        self,
        extractors: Sequence[BaseLanguageExtractor] | None = None,
    ) -> None:
        """Initializes the registry with optional initial extractors.

        Args:
            extractors (Sequence[BaseLanguageExtractor] | None, optional): Initial extractors.
        """
        self._extractors: list[BaseLanguageExtractor] = (
            list(extractors) if extractors else []
        )

    def register(self, extractor: BaseLanguageExtractor) -> None:
        """Registers a new language extractor.

        Args:
            extractor (BaseLanguageExtractor): Extractor to register.
        """
        self._extractors.append(extractor)

    def get_extractors_for_repo(
        self,
        provider: SourceFileProvider,
    ) -> list[BaseLanguageExtractor]:
        """Finds all extractors capable of handling the repository.

        Args:
            provider (SourceFileProvider): File inspection provider.

        Returns:
            list[BaseLanguageExtractor]: Extractors that returned True from can_handle.
        """
        return [ext for ext in self._extractors if ext.can_handle(provider)]


@lru_cache
def get_default_extractor_registry() -> ExtractorRegistry:
    """Factory creating and caching the default registry with built-in extractors.

    Returns:
        ExtractorRegistry: Default registry populated with standard extractors.
    """
    registry = ExtractorRegistry()
    registry.register(PythonProfileExtractor())
    return registry
