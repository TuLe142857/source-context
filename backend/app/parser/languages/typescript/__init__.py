"""TypeScript and TSX parser configurations."""

from functools import lru_cache

from app.domain.source_file import (
    SOURCE_LANGUAGE_EXTENSIONS,
    SourceLanguage,
)
from app.parser.language_registry import LanguageConfig
from app.parser.uast import BaseUASTConverter, UASTConverter

from .adapter import (
    get_tsx_adapter,
    get_tsx_language,
    get_typescript_adapter,
    get_typescript_language,
)


def _get_plain_typescript_extensions() -> list[str]:
    """Return TypeScript extensions that do not contain JSX."""

    return [
        extension
        for extension in SOURCE_LANGUAGE_EXTENSIONS[SourceLanguage.TYPESCRIPT]
        if extension != ".tsx"
    ]


def _get_tsx_extensions() -> list[str]:
    """Return extensions requiring the TSX grammar."""

    return [
        extension
        for extension in SOURCE_LANGUAGE_EXTENSIONS[SourceLanguage.TYPESCRIPT]
        if extension == ".tsx"
    ]


@lru_cache
def get_typescript_converter() -> UASTConverter:
    """Return the converter for plain TypeScript."""

    return BaseUASTConverter(
        get_typescript_adapter(),
    )


@lru_cache
def get_tsx_converter() -> UASTConverter:
    """Return the converter for TSX."""

    return BaseUASTConverter(
        get_tsx_adapter(),
    )


@lru_cache
def get_typescript_language_config() -> LanguageConfig:
    """Return the plain TypeScript parser configuration."""

    return LanguageConfig(
        name="typescript",
        language_factory=get_typescript_language,
        converter_factory=get_typescript_converter,
        extensions=_get_plain_typescript_extensions(),
    )


@lru_cache
def get_tsx_language_config() -> LanguageConfig:
    """Return the internal TSX parser configuration."""

    return LanguageConfig(
        name="tsx",
        language_factory=get_tsx_language,
        converter_factory=get_tsx_converter,
        extensions=_get_tsx_extensions(),
    )


__all__ = [
    "get_tsx_language_config",
    "get_typescript_language_config",
]
