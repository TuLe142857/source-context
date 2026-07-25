"""Tree-sitter adapter for JavaScript and JSX."""

from functools import lru_cache
from pathlib import Path

import tree_sitter_javascript
from tree_sitter import Language, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    LanguageAdapter,
)


@lru_cache
def get_language() -> Language:
    """Return the JavaScript Tree-sitter language."""

    return Language(
        tree_sitter_javascript.language(),
    )


@lru_cache
def get_query_str() -> str:
    """Load the JavaScript UAST query."""

    query_path = Path(__file__).parent / "query.scm"

    if not query_path.is_file():
        raise RuntimeError(
            f"Cannot load JavaScript query: {query_path}",
        )

    return query_path.read_text(
        encoding="utf-8",
    )


@lru_cache
def get_query() -> Query:
    """Compile the JavaScript UAST query."""

    return Query(
        get_language(),
        get_query_str(),
    )


class JavaScriptAdapter(LanguageAdapter):
    """Convert JavaScript Tree-sitter captures into UAST nodes."""

    def __init__(self) -> None:
        super().__init__(
            language_name="javascript",
            query=get_query(),
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
def get_adapter() -> LanguageAdapter:
    """Return the cached JavaScript adapter."""

    return JavaScriptAdapter()
