"""Tree-sitter adapters for TypeScript and TSX."""

from functools import lru_cache
from pathlib import Path

import tree_sitter_typescript
from tree_sitter import Language, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    LanguageAdapter,
)


@lru_cache
def get_typescript_language() -> Language:
    """Return the plain TypeScript Tree-sitter language."""

    return Language(
        tree_sitter_typescript.language_typescript(),
    )


@lru_cache
def get_tsx_language() -> Language:
    """Return the JSX-aware TypeScript Tree-sitter language."""

    return Language(
        tree_sitter_typescript.language_tsx(),
    )


@lru_cache
def get_query_str() -> str:
    """Load the shared TypeScript and TSX UAST query."""

    query_path = Path(__file__).parent / "query.scm"

    if not query_path.is_file():
        raise RuntimeError(
            f"Cannot load TypeScript query: {query_path}",
        )

    return query_path.read_text(
        encoding="utf-8",
    )


@lru_cache
def get_typescript_query() -> Query:
    """Compile the query against the TypeScript grammar."""

    return Query(
        get_typescript_language(),
        get_query_str(),
    )


@lru_cache
def get_tsx_query() -> Query:
    """Compile the query against the TSX grammar."""

    return Query(
        get_tsx_language(),
        get_query_str(),
    )


class TypeScriptAdapter(LanguageAdapter):
    """Convert TypeScript-family captures into UAST nodes."""

    def __init__(
        self,
        *,
        query: Query,
    ) -> None:
        super().__init__(
            language_name="typescript",
            query=query,
            handlers=[
                BaseMetadataCaptureHandler(),
                BaseNodeCaptureHandler(
                    capture_patterns=[
                        "definition.*",
                        "reference.*",
                        "dependency.*",
                    ],
                ),
            ],
        )


@lru_cache
def get_typescript_adapter() -> LanguageAdapter:
    """Return the adapter compiled for plain TypeScript."""

    return TypeScriptAdapter(
        query=get_typescript_query(),
    )


@lru_cache
def get_tsx_adapter() -> LanguageAdapter:
    """Return the adapter compiled for TSX."""

    return TypeScriptAdapter(
        query=get_tsx_query(),
    )
