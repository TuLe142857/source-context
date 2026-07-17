from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from tree_sitter import Node

__all__ = [
    "UASTNode",
    "ContainerNode",
    "DefinitionNode",
    "TypeDefinitionNode",
    "FunctionNode",
    "VariableNode",
    "DependencyNode",
    "ImportNode",
    "ExportNode",
    "ReferenceNode",
    "CallNode",
    "AttributeAccessNode",
    "TypeReferenceNode",
    "UASTNodeFactory",
    "UASTNodeBuilder",
]


@dataclass(kw_only=True)
class UASTNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    node_type: str

    name: str | None = None

    start_point: tuple[int, int]
    """[row, column]"""

    end_point: tuple[int, int]
    """[row, column]"""

    start_byte: int

    end_byte: int

    source: str | None = None

    docstring: str | None = None

    parent_id: str | None = None
    children: list["UASTNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ====================================================
#       CONTAINER: Project, Module, File
# ====================================================
@dataclass(kw_only=True)
class ContainerNode(UASTNode):
    node_type: Literal["container"] = "container"
    kind: Literal["project", "module", "file"]
    language: str | None = None
    path: str | None = None
    source_bytes: bytes | None = None


# ====================================================
#       DEFINITION: class, enum, interface, function, ...
# ====================================================


@dataclass(kw_only=True)
class DefinitionNode(UASTNode):
    visibility: str | None = None
    modifiers: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class TypeDefinitionNode(DefinitionNode):
    node_type: Literal["type-definition"] = "type-definition"
    kind: Literal["class", "interface", "enum", "struct", "trait", "protocol"] = "class"

    base_types: list[str] = field(default_factory=list)
    is_abstract: bool = False
    enum_values: list[str] = field(default_factory=list)
    """For kind=enum only"""


@dataclass(kw_only=True)
class FunctionNode(DefinitionNode):
    node_type: Literal["function"] = "function"
    kind: Literal["function", "method", "constructor", "lambda"] = "function"

    return_type: str | None = None

    is_async: bool = False

    is_generator: bool = False
    """Python yield, JS function"""

    is_static: bool = False
    """ static method"""

    is_abstract: bool = False
    """abstract method"""

    is_override: bool = False
    """""@Override Java, override Kotlin/Swift..."""


@dataclass(kw_only=True)
class VariableNode(DefinitionNode):
    node_type: Literal["variable"] = "variable"
    kind: Literal["variable", "constant", "field", "parameter"] = "variable"

    type_annotation: str | None = None
    initial_value: str | None = None


# ====================================================
#       DEPENDENCY
# ====================================================
@dataclass(kw_only=True)
class DependencyNode(UASTNode):
    pass


@dataclass(kw_only=True)
class ImportNode(DependencyNode):
    node_type: Literal["import"] = "import"

    module_path: str | None = None


@dataclass(kw_only=True)
class ExportNode(DependencyNode):
    node_type: Literal["export"] = "export"


# ====================================================
#       REFERENCE: call, attribute, type
# ====================================================


@dataclass(kw_only=True)
class ReferenceNode(UASTNode):
    pass


@dataclass(kw_only=True)
class CallNode(ReferenceNode):
    node_type: Literal["call"] = "call"


@dataclass(kw_only=True)
class AttributeAccessNode(ReferenceNode):
    node_type: Literal["attribute_access"] = "attribute_access"


@dataclass(kw_only=True)
class TypeReferenceNode(ReferenceNode):
    node_type: Literal["type_reference"] = "type_reference"


class UASTNodeFactory:
    """
    Map from capture name to node type
    """

    type FactoryConfig = dict[str, type[UASTNode] | tuple[type[UASTNode], dict[str, Any]]]

    def __init__(self, registry: dict[str, type[UASTNode] | tuple[type[UASTNode], dict[str, Any]]] | None = None):
        """
        Args:
            registry:
                - dict[str, type[UASTNode]]: map capture name(str) to UASTNode type.
                - dict[str, tuple(type[UASTNode], dict[str, Any])]: map capture name(str) to UASTNode type, contain
                  default dict[str, Any] to pass as keyword-arguments when call constructor. This keyword-arguments can
                  be overridden.


        Default config:
            ...

        """
        if registry is None:
            self._registry: dict[str, type[UASTNode] | tuple[type[UASTNode], dict[str, Any]]] = {
                # fmt: off
                "container.project": (ContainerNode, {"kind": "project"}),
                "container.module": (ContainerNode, {"kind": "module"}),
                "container.file": (ContainerNode, {"kind": "file"}),
                "definition.interface": (TypeDefinitionNode, {"kind": "interface"}),
                "definition.enum": (TypeDefinitionNode, {"kind": "enum"}),
                "definition.struct": (TypeDefinitionNode, {"kind": "struct"}),
                "definition.trait": (TypeDefinitionNode, {"kind": "trait"}),
                "definition.protocol": (TypeDefinitionNode, {"kind": "protocol"}),
                "definition.class": (TypeDefinitionNode, {"kind": "class"}),
                "definition.method": (FunctionNode, {"kind": "method"}),
                "definition.constructor": (FunctionNode, {"kind": "constructor"}),
                "definition.lambda": (FunctionNode, {"kind": "lambda"}),
                "definition.function": (FunctionNode, {"kind": "function"}),
                "definition.field": (VariableNode, {"kind": "field"}),
                "definition.constant": (VariableNode, {"kind": "constant"}),
                "definition.parameter": (VariableNode, {"kind": "parameter"}),
                "definition.variable": (VariableNode, {"kind": "variable"}),
                "dependence.import": ImportNode,
                "dependence.export": ExportNode,
                "reference.call": CallNode,
                "reference.attribute": AttributeAccessNode,
                "reference.type": TypeReferenceNode,
                # fmt: on
            }
        else:
            self._registry = registry

    @property
    def registry(self) -> FactoryConfig:
        return self._registry

    @staticmethod
    def _validate_config(config: FactoryConfig) -> bool:
        return True

    def create(self, capture_name: str, **kwargs: Any) -> UASTNode:
        """

        Args:
            capture_name: capture name
            **kwargs: keyword arguments to pass to the constructor. Can override default keyword arguments of this
                      factory.

        Returns:

        """
        config = self._registry.get(capture_name, UASTNode)

        node_class: type[UASTNode]
        default_kwargs: dict[str, Any]

        if isinstance(config, tuple):
            if not (len(config) == 2 and isinstance(config[0], type) and isinstance(config[1], dict)):
                raise ValueError("Invalid UASTNode config")
            node_class = config[0]
            default_kwargs = config[1]
        elif isinstance(config, type) and issubclass(config, UASTNode):
            node_class = config
            if config is UASTNode:
                default_kwargs = {"node_type": "generic"}
            else:
                default_kwargs = {}
        else:
            raise ValueError("Invalid UASTNode config")

        merged_kwargs: dict[str, Any] = default_kwargs | kwargs
        return node_class(**merged_kwargs)


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
        self.children: list["UASTNode"] = list()
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

    def add_child(self, child: "UASTNode") -> UASTNodeBuilder:
        self.children.append(child)
        return self

    def set_metadata(self, key: str, value: Any) -> UASTNodeBuilder:
        self.metadata[key] = value
        return self

    def set(self, keyword: str, value: Any) -> UASTNodeBuilder:
        self.attributes_map[keyword] = value
        return self

    def build(self, node_factory: UASTNodeFactory) -> UASTNode:
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
