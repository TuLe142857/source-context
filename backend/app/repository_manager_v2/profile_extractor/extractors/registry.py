"""Registry for language-specific subproject extractors."""

from functools import lru_cache

from app.repository_manager_v2.profile_extractor.extractors.base import (
    BaseSubprojectExtractor,
)
from app.repository_manager_v2.profile_extractor.extractors.javascript import (
    JavaScriptSubprojectExtractor,
)
from app.repository_manager_v2.profile_extractor.extractors.python import (
    PythonSubprojectExtractor,
)


class SubprojectExtractorRegistry:
    """Registry managing available language sub-project extractors."""

    def __init__(self) -> None:
        """Initializes empty extractor registry."""
        self._extractors: dict[str, BaseSubprojectExtractor] = {}

    def register(self, extractor: BaseSubprojectExtractor) -> None:
        """Registers an extractor for all its supported languages.

        Args:
            extractor (BaseSubprojectExtractor): Subproject extractor instance.
        """
        for lang in extractor.supported_languages:
            self._extractors[lang.lower()] = extractor

    def get(self, language: str) -> BaseSubprojectExtractor | None:
        """Retrieves an extractor matching the language.

        Args:
            language (str): Language name (e.g. 'python', 'typescript').

        Returns:
            BaseSubprojectExtractor | None: Matching extractor if registered.
        """
        return self._extractors.get(language.lower())


@lru_cache
def get_default_subproject_registry() -> SubprojectExtractorRegistry:
    """Factory creating and caching default registry with built-in language extractors.

    Returns:
        SubprojectExtractorRegistry: Registry with Python and JavaScript/TypeScript extractors.
    """
    registry = SubprojectExtractorRegistry()
    registry.register(PythonSubprojectExtractor())
    registry.register(JavaScriptSubprojectExtractor())
    return registry
