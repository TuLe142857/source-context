from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(kw_only=True)
class UASTNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Node id, default is random uuid4()"""

    node_type: str
    """node_type"""

    name: str | None = None
    """Node name. In most case is identifier like name of class, name of method, etc."""

    start_point: tuple[int, int]
    """[row, column]"""
    end_point: tuple[int, int]
    """[row, column]"""

    start_byte: int
    """start byte index(in file). start from 0"""
    end_byte: int
    "end byte index(in file). start from 0"

    docstring: str | None = None
    """Docstring of this node as string"""

    parent_id: str | None = None
    """This node's parent id."""
    children: list[UASTNode] = field(default_factory=list)
    """This node's children."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata as dict."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "docstring": self.docstring,
            "parent_id": self.parent_id,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
        }


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
    """For file node only. File source code as bytes."""

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "kind": self.kind,
            "language": self.language,
            "path": self.path,
            "source_bytes": self.source_bytes.decode() if self.source_bytes else None,
        }
        return super().to_dict() | additional_data


# ====================================================
#       DEFINITION: class, enum, interface, function, ...
# ====================================================


@dataclass(kw_only=True)
class DefinitionNode(UASTNode):
    visibility: str | None = None
    modifiers: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "visibility": self.visibility,
            "modifiers": self.modifiers,
            "decorators": self.decorators,
        }
        return super().to_dict() | additional_data


@dataclass(kw_only=True)
class TypeDefinitionNode(DefinitionNode):
    node_type: Literal["type-definition"] = "type-definition"
    kind: Literal[
        "class", "interface", "enum", "struct", "trait", "protocol", "type_alias"
    ] = "class"

    base_types: list[str] = field(default_factory=list)
    is_abstract: bool = False
    enum_values: list[str] = field(default_factory=list)
    """For kind=enum only"""

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "kind": self.kind,
            "base_types": self.base_types,
            "is_abstract": self.is_abstract,
            "enum_values": self.enum_values,
        }
        return super().to_dict() | additional_data


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

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "kind": self.kind,
            "return_type": self.return_type,
            "is_async": self.is_async,
            "is_generator": self.is_generator,
            "is_static": self.is_static,
            "is_abstract": self.is_abstract,
            "is_override": self.is_override,
        }
        return super().to_dict() | additional_data


@dataclass(kw_only=True)
class VariableNode(DefinitionNode):
    node_type: Literal["variable"] = "variable"
    kind: Literal["variable", "constant", "field", "parameter"] = "variable"

    data_type: str | None = None
    initial_value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "kind": self.kind,
            "data_type": self.data_type,
            "initial_value": self.initial_value,
        }
        return super().to_dict() | additional_data


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

    imported_names: list[str] = field(default_factory=list)

    alias: dict[str, str] = field(default_factory=dict)
    """Map imported_name to its alias"""

    def to_dict(self) -> dict[str, Any]:
        additional_data = {
            "module_path": self.module_path,
        }
        return super().to_dict() | additional_data


@dataclass(kw_only=True)
class ExportNode(DependencyNode):
    node_type: Literal["export"] = "export"

    exported_names: list[str] = field(default_factory=list)

    alias: dict[str, str] = field(default_factory=dict)


# ====================================================
#       REFERENCE: call, attribute, type
# ====================================================


@dataclass(kw_only=True)
class ReferenceNode(UASTNode):
    pass


@dataclass(kw_only=True)
class CallNode(ReferenceNode):
    node_type: Literal["call"] = "call"

    subject: str | None = None
    """
    Example:
        caculator.sum(a, b)
            - name: sum
            - subject: calculator

        print("hi")
            - name: print
            - subject: None
    """


@dataclass(kw_only=True)
class AttributeAccessNode(ReferenceNode):
    node_type: Literal["attribute_access"] = "attribute_access"


@dataclass(kw_only=True)
class TypeReferenceNode(ReferenceNode):
    node_type: Literal["type_reference"] = "type_reference"

    namespace: str | None = None

    type_arguments: list[str] = field(default_factory=list)
    """For generic type like Map<str, int>"""
