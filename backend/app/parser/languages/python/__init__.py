"""Python parser configuration."""

from functools import lru_cache

from app.domain.source_file import (
    SOURCE_LANGUAGE_EXTENSIONS,
    SourceLanguage,
)
from app.parser.language_registry import LanguageConfig
from app.parser.uast import BaseUASTConverter, UASTConverter

from .adapter import get_adapter, get_language


@lru_cache
def get_converter() -> UASTConverter:
    """Return the cached Python UAST converter."""

    return BaseUASTConverter(get_adapter())


@lru_cache
def get_language_config() -> LanguageConfig:
    """Return the Python parser configuration."""

    return LanguageConfig(
        name=SourceLanguage.PYTHON.value,
        language_factory=get_language,
        converter_factory=get_converter,
        extensions=list(
            SOURCE_LANGUAGE_EXTENSIONS[SourceLanguage.PYTHON],
        ),
    )


__all__ = ["get_language_config"]
