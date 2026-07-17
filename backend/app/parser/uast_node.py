from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


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
    children: list[UASTNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "source": self.source,
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
