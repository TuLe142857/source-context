from functools import lru_cache
from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    LanguageAdapter,
)


@lru_cache()
def get_language() -> Language:
    return Language(tree_sitter_python.language())


@lru_cache()
def get_query_str() -> str:
    path = Path(__file__).parent / "query.scm"
    if (not path.exists()) or (not path.is_file()):
        raise RuntimeError("Cannot load Python query: path not exits or not a file")
    return path.read_text()


@lru_cache()
def get_query() -> Query:
    language = get_language()
    query_str = get_query_str()
    return Query(language, query_str)


class PythonAdapter(LanguageAdapter):
    def __init__(self) -> None:
        super().__init__(
            language_name="python",
            query=get_query(),
            handlers=[
                BaseMetadataCaptureHandler(),
                BaseNodeCaptureHandler(
                    capture_patterns=["definition.*", "reference.*", "dependency.*"]
                ),
            ],
        )


@lru_cache()
def get_adapter() -> LanguageAdapter:
    return PythonAdapter()
