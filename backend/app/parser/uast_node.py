import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from tree_sitter import Node


@dataclass(kw_only=True)
class UastNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    name: str | None = None

    node_type: str

    start_point: tuple[int, int]
    """[row, column]"""

    end_point: tuple[int, int]
    """[row, column]"""

    start_byte: int

    end_byte: int

    language: str | None

    file_path: str | None = None

    source: str | None = None
    docstring: str | None = None

    parent_id: str | None = None
    children: list["UastNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class FileNode(UastNode):
    node_type: Literal["file"] = "file"


@dataclass(kw_only=True)
class ClassNode(UastNode):
    node_type: Literal["class"] = "class"


@dataclass(kw_only=True)
class FunctionNode(UastNode):
    node_type: Literal["function"] = "function"


@dataclass(kw_only=True)
class ParameterNode(UastNode):
    """
    Function/Methods parameters
    """

    data_type: str
    default_value: str


@dataclass(kw_only=True)
class ExpressionNode(UastNode):
    node_type: Literal["expression"] = "expression"


@dataclass(kw_only=True)
class ReferenceNode(UastNode):
    pass


@dataclass(kw_only=True)
class CallNode(ReferenceNode):
    node_type: Literal["call"] = "call"


class UASTNodeFactory(Protocol):
    def create(self, capture_name: str, **kwargs: Any) -> UastNode:
        pass


class UASTNodeBuilder:
    def __init__(
        self,
        capture_name: str,
        node_id: str | None = None,
    ) -> None:
        """

        Args:
            capture_name: tree-sitter query capture name
            node_id: node id. Default is None. If not provided, node_id will be assigned with random uuid. Node id is
                `immutable` after init builder and can be read as a property with `.id`.
        """
        self.capture_name = capture_name

        self._node_id = node_id if (node_id is not None) else str(uuid.uuid4())
        self.name: str | None = None
        self.node_type: str | None = None
        self.start_point: tuple[int, int] | None = None
        self.end_point: tuple[int, int] | None = None
        self.start_byte: int | None = None
        self.end_byte: int | None = None
        self.language: str | None = None
        self.file_path: str | None = None
        self.source: str | None = None
        self.docstring: str | None = None
        self.parent_id: str | None = None
        self.children: list["UastNode"] = list()
        self.metadata: dict[str, Any] = dict()

        self.attributes_map: dict[str, Any] = dict()

    @staticmethod
    def from_ts_node(ts_node: Node, capture_name: str, node_id: str | None = None) -> "UASTNodeBuilder":
        """

        Args:
            ts_node: tree-sitter node(source node)
            capture_name: capture name
            node_id: uast node id for builder

        Returns:

        """
        builder = UASTNodeBuilder(capture_name, node_id)
        builder.set_start_point((ts_node.start_point.row, ts_node.start_point.column))
        builder.set_end_point((ts_node.end_point.row, ts_node.end_point.column))
        builder.set_start_byte(ts_node.start_byte)
        builder.set_end_byte(ts_node.end_byte)
        return builder

    @property
    def id(self) -> str:
        """
        Node id is immutable after init builder and can be read as a property with `id`.

        Returns: node id as str

        """
        return self._node_id

    def set_name(self, name: str) -> "UASTNodeBuilder":
        self.name = name
        return self

    def set_node_type(self, node_type: str) -> "UASTNodeBuilder":
        self.node_type = node_type
        return self

    def set_start_point(self, start_point: tuple[int, int]) -> "UASTNodeBuilder":
        self.start_point = start_point
        return self

    def set_end_point(self, end_point: tuple[int, int]) -> "UASTNodeBuilder":
        self.end_point = end_point
        return self

    def set_start_byte(self, start_byte: int) -> "UASTNodeBuilder":
        self.start_byte = start_byte
        return self

    def set_end_byte(self, end_byte: int) -> "UASTNodeBuilder":
        self.end_byte = end_byte
        return self

    def set_language(self, language: str) -> "UASTNodeBuilder":
        self.language = language
        return self

    def set_file_path(self, file_path: str) -> "UASTNodeBuilder":
        self.file_path = file_path
        return self

    def set_source(self, source: str) -> "UASTNodeBuilder":
        self.source = source
        return self

    def set_docstring(self, docstring: str) -> "UASTNodeBuilder":
        self.docstring = docstring
        return self

    def set_parent_id(self, parent_id: str) -> "UASTNodeBuilder":
        self.parent_id = parent_id
        return self

    def add_child(self, child: "UastNode") -> "UASTNodeBuilder":
        self.children.append(child)
        return self

    def set_metadata(self, key: str, value: Any) -> "UASTNodeBuilder":
        self.metadata[key] = value
        return self

    def set(self, keyword: str, value: Any) -> "UASTNodeBuilder":
        self.attributes_map[keyword] = value
        return self

    def build(self, node_factory: UASTNodeFactory) -> UastNode:
        self.attributes_map["id"] = self._node_id
        self.attributes_map["metadata"] = self.metadata

        if self.name is not None:
            self.attributes_map["name"] = self.name
        if self.node_type is not None:
            self.attributes_map["nodeUASTNodeBuilder_type"] = self.node_type
        if self.start_point is not None:
            self.attributes_map["start_point"] = self.start_point
        if self.end_point is not None:
            self.attributes_map["end_point"] = self.end_point
        if self.start_byte is not None:
            self.attributes_map["start_byte"] = self.start_byte
        if self.end_byte is not None:
            self.attributes_map["end_byte"] = self.end_byte
        if self.language is not None:
            self.attributes_map["language"] = self.language
        if self.file_path is not None:
            self.attributes_map["filUASTNodeBuildere_path"] = self.file_path
        if self.docstring is not None:
            self.attributes_map["docstring"] = self.docstring
        if self.parent_id is not None:
            self.attributes_map["parent_id"] = self.parent_id
        if self.children is not None:
            self.attributes_map["children"] = self.children

        return node_factory.create(self.capture_name, **self.attributes_map)
