from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Mapping, Sequence

from tree_sitter import Language, Parser

from .exc import UnsupportedLanguageError
from .uast import UASTConverter


@dataclass(frozen=True, kw_only=True)
class LanguageConfig:
    name: str
    """Language name. Always lowercase."""

    language_factory: Callable[[], Language]
    """Language factory method."""

    converter_factory: Callable[[], UASTConverter]
    """UASTConverter factory method."""

    extensions: list[str] = field(default_factory=list)
    """File extensions of language. Default empty list."""

    filename_patterns: list[str] = field(default_factory=list)
    """File patterns of language. Default empty list."""

    def __post_init__(self) -> None:
        if len(self.extensions) != len(set(self.extensions)):
            duplicates = [
                name for name, count in Counter(self.extensions).items() if count > 1
            ]
            raise ValueError(
                f"Duplicate file extensions for language '{self.name}': {duplicates}"
            )
        if len(self.filename_patterns) != len(set(self.filename_patterns)):
            duplicates = [
                name
                for name, count in Counter(self.filename_patterns).items()
                if count > 1
            ]
            raise ValueError(
                f"Duplicate filename patterns for language '{self.name}': {duplicates}"
            )

    def match(self, filename: str) -> bool:
        """
        Check if filename matches this language config(extensions, patterns).
        Args:
            filename: filename to check. Filename can include directory and separator

        Returns: `true` if filename matches this language, else `false`

        """
        path = Path(filename)
        match_pattern = any(
            [fnmatch(path.name, pattern) for pattern in self.filename_patterns]
        )
        match_extension = path.suffix in self.extensions
        return match_pattern or match_extension


class LanguageRegistry:
    def __init__(self, configs: Sequence[LanguageConfig] | list[LanguageConfig]):
        language_names = [config.name for config in configs]
        language_patterns = [
            pattern for config in configs for pattern in config.filename_patterns
        ]
        language_extensions = [
            extension for config in configs for extension in config.extensions
        ]

        if len(language_names) != len(set(language_names)):
            duplicates = [
                name for name, count in Counter(language_names).items() if count > 1
            ]
            raise ValueError(f"Duplicate language names: {duplicates}")

        if len(language_patterns) != len(set(language_patterns)):
            duplicates = [
                name for name, count in Counter(language_patterns).items() if count > 1
            ]
            raise ValueError(f"Duplicate language patterns: {duplicates}")
        if len(language_extensions) != len(set(language_extensions)):
            duplicates = [
                name
                for name, count in Counter(language_extensions).items()
                if count > 1
            ]
            raise ValueError(f"Duplicate language extensions: {duplicates}")

        self._configs: dict[str, LanguageConfig] = {
            config.name: config for config in configs
        }
        self._supported_languages: Sequence[str] = tuple(language_names)
        self._supported_file_patterns: Sequence[str] = tuple(language_patterns)
        self._supported_file_extensions = tuple(language_extensions)
        self._languages_cache: dict[str, Language] = {}

    @property
    def supported_languages(self) -> Sequence[str]:
        return self._supported_languages

    @property
    def supported_file_patterns(self) -> Sequence[str]:
        return self._supported_file_patterns

    @property
    def supported_file_extensions(self) -> Sequence[str]:
        return self._supported_file_extensions

    @property
    def configs(self) -> Mapping[str, LanguageConfig]:
        """
        Returns:
            Mapping[language_name, LanguageConfig]
        """
        return self._configs

    def resolve_language_name(self, filename: str) -> str:
        """
        Resolve the language name from the filename.

        Args:
            filename: filename to resolve.

        Returns:
            language name as string

        Raises:
            UnsupportedLanguageError

        """
        for language_name, config in self.configs.items():
            if config.match(filename):
                return language_name
        raise UnsupportedLanguageError(
            f"No Supported Language for file name: {filename}"
        )

    def get_language(self, lang_name: str) -> Language:
        """
        Get tree-sitter Language object for language name.

        Args:
            lang_name: language name.

        Returns:
            Language object.

        Raises:
            UnsupportedLanguageError

        """
        if lang_name not in self._configs:
            raise UnsupportedLanguageError(f"Unsupported Language {lang_name}")
        language = self._languages_cache.get(lang_name)
        if language is None:
            config = self._configs[lang_name]
            language = config.language_factory()
            self._languages_cache[lang_name] = language
        return language

    def get_language_for_file(self, filename: str) -> Language:
        """
        Get tree-sitter Language object for filename.

        Args:
            filename: file name.

        Returns:
            Language object.

        Raises:
            UnsupportedLanguageError

        """
        return self.get_language(self.resolve_language_name(filename))

    def get_parser(self, lang_name: str) -> Parser:
        """
        Get tree-sitter Parser by language name.

        Args:
            lang_name: language name.

        Returns:
            Parser object.

        Raises:
            UnsupportedLanguageError

        """
        if lang_name not in self._configs:
            raise UnsupportedLanguageError(f"Unsupported Language {lang_name}")
        language = self.get_language(lang_name)
        return Parser(language)

    def get_parser_for_file(self, filename: str) -> Parser:
        """
        Get tree-sitter Parser by filename.

        Args:
            filename: file name.

        Returns:
            Parser object.

        Raises:
            UnsupportedLanguageError

        """
        return self.get_parser(self.resolve_language_name(filename))

    def get_converter(self, lang_name: str) -> UASTConverter:
        """
        Get UASTConverter by language name.

        Args:
            lang_name: language name

        Returns:
            UASTConverter object.

        Raises:
            UnsupportedLanguageError

        """
        if lang_name not in self._configs:
            raise UnsupportedLanguageError(f"Unsupported Language {lang_name}")
        config = self._configs[lang_name]
        return config.converter_factory()

    def get_converter_for_file(self, filename: str) -> UASTConverter:
        """
        Get UASTConverter by filename.

        Args:
            filename: file name

        Returns:
            UASTConverter object.

        Raises:
            UnsupportedLanguageError

        """
        return self.get_converter(self.resolve_language_name(filename))
