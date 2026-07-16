from functools import lru_cache
from pathlib import Path
from typing import Any, Type

import tree_sitter_python
from tree_sitter import Language, Node, Query

from app.parser import (
    BuildContext,
    CallNode,
    CaptureHandler,
    ClassNode,
    FileNode,
    FunctionNode,
    LanguageAdapter,
    ReferenceNode,
    UastNode,
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
            node_factory=self.PythonNodeFactory(),
            handlers=[],
        )

    class PythonNodeFactory(UASTNodeFactory):
        def __init__(self) -> None:
            self._registry: dict[str, Type[UastNode]] = {
                "definition.file": FileNode,
                "definition.class": ClassNode,
                "definition.function": FunctionNode,
                "definition.method": FunctionNode,
                "reference.call": CallNode,
                "reference.type": ReferenceNode,
            }

        def create(self, capture_name: str, **kwargs: Any) -> UastNode:
            node_class = self._registry.get(capture_name, UastNode)
            if node_class is UastNode or ("node_type" not in kwargs):
                kwargs["node_type"] = capture_name.replace("definition.", "").replace("reference.", "")
            kwargs["language"] = "python"

            return node_class(**kwargs)

    class MetadataHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if capture_name not in ("name", "doc", "comment", "decorator", "modifier"):
                return False

            text_bytes = ts_child.text
            text = text_bytes.decode("utf-8") if text_bytes is not None else ""

            if capture_name == "name":
                parent_builder.set_name(text)
            elif capture_name == "doc":
                parent_builder.set_docstring(text)
            elif capture_name == "comment":
                pass
            elif capture_name == "decorator":
                parent_builder.set_metadata("decorator", text)
            return True

    class DefinitionHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("definition"):
                return False

            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder

    class ReferenceHandler(CaptureHandler):
        def handle(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if not capture_name.startswith("reference"):
                return False
            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            return builder


@lru_cache()
def get_adapter() -> LanguageAdapter:
    return PythonAdapter()
