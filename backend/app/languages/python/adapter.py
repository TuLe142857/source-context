from functools import lru_cache
from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Node, Query

from app.parser import (
    BuildContext,
    CaptureHandler,
    DefaultCaptureHandler,
    LanguageAdapter,
    UASTNodeBuilder,
    UASTNodeFactory,
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
            node_factory=UASTNodeFactory(),
            handlers=[
                DefaultCaptureHandler.ContainerHandler(),
                DefaultCaptureHandler.DefinitionHandler(),
                DefaultCaptureHandler.DependencyHandler(),
                DefaultCaptureHandler.ReferenceHandler(),
                self.PythonMetadataHandler(),
            ],
        )

    class PythonMetadataHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("meta"):
                return False
            meta_type = capture_name.split(".")[-1]

            text_bytes = ts_child.text
            text = text_bytes.decode("utf-8") if text_bytes is not None else ""

            match meta_type:
                case "name":
                    parent_builder.set_name(text)
                case "doc":
                    parent_builder.set_docstring(text)
                case "comment":
                    pass
                case "visibility":
                    pass
                case "modifier":
                    pass
                case "decorator":
                    pass
                case "return_type":
                    pass
                case "type":
                    pass
                case "base_type":
                    pass
                case "value":
                    pass
                case "init_value":
                    pass
                case _:
                    pass

            return True


@lru_cache()
def get_adapter() -> LanguageAdapter:
    return PythonAdapter()
