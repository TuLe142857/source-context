from __future__ import annotations

import uuid
from typing import Any

from tree_sitter import Node

from .node import (
    AttributeAccessNode,
    CallNode,
    ContainerNode,
    ExportNode,
    FunctionNode,
    ImportNode,
    TypeDefinitionNode,
    TypeReferenceNode,
    UASTNode,
    VariableNode,
)
from .types import CaptureType


class UASTNodeFactory:
    """
    Map from capture name to node type
    """

    type FactoryConfig = dict[
        CaptureType, type[UASTNode] | tuple[type[UASTNode], dict[str, Any]]
    ]

    def __init__(self, registry: FactoryConfig | None = None):
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
            self._registry: UASTNodeFactory.FactoryConfig = {
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
                "dependency.import": ImportNode,
                "dependency.export": ExportNode,
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

    def create(self, capture_name: CaptureType, **kwargs: Any) -> UASTNode:
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
            if not (
                len(config) == 2
                and isinstance(config[0], type)
                and isinstance(config[1], dict)
            ):
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
        capture_name: CaptureType,
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
        self.node_type: str | None = None
        self.name: str | None = None
        self.start_point: tuple[int, int] | None = None
        self.end_point: tuple[int, int] | None = None
        self.start_byte: int | None = None
        self.end_byte: int | None = None
        self.docstring: str | None = None
        self.parent_id: str | None = None
        self.children: list["UASTNode"] = list()
        self.metadata: dict[str, Any] = dict()

        # additional attributes for subclass of UASTNode
        # It will be pass to constructor as keyword-argument
        self.attributes_map: dict[str, Any] = dict()

    @staticmethod
    def from_ts_node(
        ts_node: Node, capture_name: str, node_id: str | None = None
    ) -> "UASTNodeBuilder":
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

    def set_name(self, name: str | None) -> "UASTNodeBuilder":
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

    def set_docstring(self, docstring: str | None) -> "UASTNodeBuilder":
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

    def append(self, keyword: str, value: Any) -> UASTNodeBuilder:
        """
        Append ``value`` to a list-valued attribute, creating the list if absent.

        Use for attributes accumulated across multiple captures on the same
        parent (e.g. ``modifiers``, ``decorators``, ``base_types``, ``enum_values``).
        """
        self.attributes_map.setdefault(keyword, []).append(value)
        return self

    def build(self, node_factory: UASTNodeFactory) -> UASTNode:
        kwargs: dict[str, Any] = self.attributes_map.copy()

        kwargs["id"] = self._node_id
        kwargs["metadata"] = self.metadata

        if self.name is not None:
            kwargs["name"] = self.name
        if self.node_type is not None:
            kwargs["node_type"] = self.node_type
        if self.start_point is not None:
            kwargs["start_point"] = self.start_point
        if self.end_point is not None:
            kwargs["end_point"] = self.end_point
        if self.start_byte is not None:
            kwargs["start_byte"] = self.start_byte
        if self.end_byte is not None:
            kwargs["end_byte"] = self.end_byte
        if self.docstring is not None:
            kwargs["docstring"] = self.docstring
        if self.parent_id is not None:
            kwargs["parent_id"] = self.parent_id
        if self.children is not None:
            kwargs["children"] = self.children

        return node_factory.create(self.capture_name, **kwargs)
