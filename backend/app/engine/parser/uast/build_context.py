from __future__ import annotations

from typing import Any

from tree_sitter import Node

from .node_builder import UASTNodeBuilder


class BuildContext:
    class BuildScope:
        def __init__(self, builder: UASTNodeBuilder):
            self.builder = builder

            self.pending_metadata: dict[str, Any] = dict()
            """
            Pending metadata that will be pass to next sibling node(Must implement logic in handler to get metadata
            from previous sibling node, then pop all metdata value when it's handled).
            """

            self.state: dict[str, Any] = dict()
            """
            Build state. Use for customization per language.
            """

    def __init__(
        self,
        file_path: str | None = None,
        language_name: str | None = None,
        source_bytes: bytes | None = None,
    ):
        self._file_path = file_path
        self._language_name = language_name
        self._source_bytes = source_bytes

        self._pending_ts_node_for_next_sibling: list[tuple[str, Node]] = []
        """In most case, use for stack metadata that will belong to next sibling node(in the same parent)"""

        self._scope: list[BuildContext.BuildScope] = []

    @property
    def file_path(self) -> str | None:
        """
        Returns:
            file path as string.

        """
        return self._file_path

    @property
    def language_name(self) -> str | None:
        """

        Returns:
            language name as string.

        """
        return self._language_name

    @property
    def source_bytes(self) -> bytes | None:
        """

        Returns:
            The whole file source code as bytes.
        """
        return self._source_bytes

    def get_text(self, ts_node: Node) -> str | None:
        """

        Args:
            ts_node: ``tree-sitter`` Node

        Returns:
            Text of this node as string.

        """
        text_bytes = ts_node.text
        if text_bytes is not None:
            return text_bytes.decode("utf-8")
        elif self.source_bytes is not None:
            text_bytes = self.source_bytes[ts_node.start_byte : ts_node.end_byte]
            try:
                return text_bytes.decode("utf-8")
            except (UnicodeDecodeError, IndexError):
                return None
        return None

    @property
    def current_scope(self) -> BuildContext.BuildScope:
        """

        Returns:
            Current ``BuildContext.BuildScope`` - parent build scope.
        """
        return self._scope[-1]

    def push_scope(self, scope: BuildContext.BuildScope) -> None:
        """
        DO NOT CALL THIS METHOD IN CAPTURE HANDLER.
        """
        self._scope.append(scope)

    def pop_scope(self) -> BuildContext.BuildScope:
        """
        DO NOT CALL THIS METHOD IN CAPTURE HANDLER.
        """
        return self._scope.pop()
