"""Application service for source parsing and UAST conversion."""

from app.domain.source_file import detect_source_language

from .contracts import (
    ParseResult,
    ParseStatus,
)
from .diagnostics import collect_parse_diagnostics
from .language_registry import LanguageRegistry
from .languages import get_language_registry


class ParserService:
    """Parse supported source code into normalized UAST results."""

    def __init__(
        self,
        registry: LanguageRegistry | None = None,
    ) -> None:
        self._registry = registry if registry is not None else get_language_registry()

    @property
    def registry(self) -> LanguageRegistry:
        """Return the registry used by this service."""

        return self._registry

    def parse_text(
        self,
        source: str,
        *,
        file_path: str,
    ) -> ParseResult:
        """Parse UTF-8 source text."""

        return self.parse_bytes(
            source.encode("utf-8"),
            file_path=file_path,
        )

    def parse_bytes(
        self,
        source_bytes: bytes,
        *,
        file_path: str,
    ) -> ParseResult:
        """Parse source bytes and return normalized UAST output."""

        normalized_path = file_path.strip()

        if not normalized_path:
            raise ValueError(
                "file_path must not be empty",
            )

        lookup_name = self._get_lookup_name(
            normalized_path,
        )

        parser_name = self._registry.resolve_language_name(
            lookup_name,
        )

        source_language = detect_source_language(
            lookup_name,
        )

        if source_language is None:
            raise RuntimeError(
                "Parser registry and source-language "
                f"catalog disagree for {lookup_name!r}.",
            )

        parser = self._registry.get_parser_for_file(
            lookup_name,
        )

        tree = parser.parse(
            source_bytes,
        )

        diagnostics = collect_parse_diagnostics(
            tree.root_node,
            source_bytes,
        )

        converter = self._registry.get_converter_for_file(
            lookup_name,
        )

        uast_root = converter.convert(
            tree,
            source_bytes=source_bytes,
            file_path=normalized_path,
        )

        status = ParseStatus.PARTIAL if diagnostics else ParseStatus.SUCCESS

        return ParseResult(
            file_path=normalized_path,
            language=source_language.value,
            parser_name=parser_name,
            status=status,
            source_size_bytes=len(source_bytes),
            diagnostics=diagnostics,
            uast_root=uast_root,
        )

    @staticmethod
    def _get_lookup_name(
        file_path: str,
    ) -> str:
        """Return a case-normalized filename for registry lookup."""

        normalized_separator_path = file_path.replace(
            "\\",
            "/",
        )

        file_name = normalized_separator_path.rsplit(
            "/",
            maxsplit=1,
        )[-1]

        if not file_name:
            raise ValueError(
                "file_path must contain a filename",
            )

        return file_name.casefold()
