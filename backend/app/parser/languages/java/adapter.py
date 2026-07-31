from functools import lru_cache
from pathlib import Path

import tree_sitter_java
from tree_sitter import Language, Node, Query

from app.parser.uast import (
    BaseMetadataCaptureHandler,
    BaseNodeCaptureHandler,
    BuildContext,
    LanguageAdapter,
    UASTNodeBuilder,
    UASTNodeFactory,
)


@lru_cache()
def get_language() -> Language:
    return Language(tree_sitter_java.language())


@lru_cache()
def get_query_str() -> str:
    path = Path(__file__).parent / "query.scm"
    if (not path.exists()) or (not path.is_file()):
        raise RuntimeError("Cannot load Java query: path not exits or not a file")
    return path.read_text()


@lru_cache()
def get_query() -> Query:
    return Query(get_language(), get_query_str())


class JavaAdapter(LanguageAdapter):
    def __init__(self) -> None:
        super().__init__(
            language_name="java",
            query=get_query(),
            node_factory=UASTNodeFactory(),
            handlers=[
                self.JavaDefinitionHandler(),
                self.JavaMetadataHandler(),
                BaseNodeCaptureHandler(capture_patterns=["dependency.*", "reference"]),
                BaseNodeCaptureHandler(capture_patterns=["reference.*"]),
            ],
        )

    class JavaDefinitionHandler(BaseNodeCaptureHandler):
        def __init__(self) -> None:
            super().__init__(capture_patterns="definition.*")

        def do_after_build(
            self,
            builder: UASTNodeBuilder,
            ts_node: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext,
        ) -> None:
            pending_metadata = context.current_scope.pending_metadata
            doc = pending_metadata.pop("meta.doc", None)
            builder.set_docstring(doc)

        def create_builder(
            self,
            capture_name: str,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext,
        ) -> UASTNodeBuilder:
            builder = UASTNodeBuilder.from_ts_node(ts_child, capture_name)
            builder.set_parent_id(parent_builder.id)
            if context is not None:
                pending_metadata = context.current_scope.pending_metadata
                doc = pending_metadata.pop("meta.doc", None)
                builder.set_docstring(doc)
            return builder

    class JavaMetadataHandler(BaseMetadataCaptureHandler):
        def handle_docstring(
            self,
            ts_child: Node,
            parent_builder: UASTNodeBuilder,
            context: BuildContext | None = None,
        ) -> bool | UASTNodeBuilder:
            if context is not None:
                context.current_scope.pending_metadata["meta.doc"] = context.get_text(
                    ts_child
                )
                return True
            return False


@lru_cache()
def get_adapter() -> LanguageAdapter:
    return JavaAdapter()
