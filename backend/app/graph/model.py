from __future__ import annotations

from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    RelationshipFrom,
    RelationshipTo,
    ArrayProperty,
    JSONProperty,
    get_config,
    BooleanProperty,
    RelationshipManager,
)

from app.parser.uast import (
    UASTNode,
    DefinitionNode,
    TypeDefinitionNode,
    FunctionNode,
    VariableNode,
    ImportNode,
    ExportNode,
    CallNode,
    TypeReferenceNode,
    AttributeAccessNode,
)
from app.core.config import settings

from typing import Self, Any

config = get_config()
config.database_url = settings.NEO4J_URI


class WorkspaceNodeModel(StructuredNode):
    __label__ = "Workspace"

    uid: int = IntegerProperty(required=True, unique_index=True)  # type: ignore[assignment]
    name: str = StringProperty(required=True)  # type: ignore[assignment]

    repositories: RelationshipManager = RelationshipTo(  # type: ignore[assignment]
        "RepositoryNodeModel", "INCLUDES"
    )


class RepositoryNodeModel(StructuredNode):
    __label__ = "Repository"

    uid: int = IntegerProperty(required=True, unique_index=True)  # type: ignore[assignment]
    name: str = StringProperty()  # type: ignore[assignment]

    branches: RelationshipManager = RelationshipTo("BranchNodeModel", "INCLUDES")  # type: ignore[assignment]
    workspace: RelationshipManager = RelationshipFrom("WorkspaceNodeModel", "INCLUDES")  # type: ignore[assignment]


class BranchNodeModel(StructuredNode):
    __label__ = "Branch"

    uid: int = IntegerProperty(required=True, unique_index=True)  # type: ignore[assignment]
    name: str = StringProperty()  # type: ignore[assignment]
    commit_hash: str = StringProperty()  # type: ignore[assignment]


class ProjectNodeModel(StructuredNode):
    __label__ = "Project"

    uid: int = IntegerProperty(required=True, unique_index=True)  # type: ignore[assignment]

    name: str = StringProperty()  # type: ignore[assignment]

    commit_hash: str = StringProperty()  # type: ignore[assignment]
    """Commit hash of this branch"""

    relative_path: str = StringProperty()  # type: ignore[assignment]
    """path from repository root"""

    files: RelationshipManager = RelationshipTo("FileNodeModel", "INCLUDES")  # type: ignore[assignment]
    branch: RelationshipManager = RelationshipFrom("BranchNodeModel", "INCLUDES")  # type: ignore[assignment]


class FileNodeModel(StructuredNode):
    __label__ = "File"

    uid: str = StringProperty(required=True, unique_index=True)  # type: ignore[assignment]

    name: str = StringProperty()  # type: ignore[assignment]
    """file name"""

    relative_path: str | None = StringProperty()  # type: ignore[assignment]
    """path from project root"""

    source_code_key: str | None = StringProperty()  # type: ignore[assignment]
    """S3 key if source code was saved on S3"""

    children: RelationshipManager = RelationshipTo("UASTNodeModel", "DECLARE")  # type: ignore[assignment]
    project: RelationshipManager = RelationshipFrom("ProjectNodeModel", "INCLUDES")  # type: ignore[assignment]


class UASTNodeModel(StructuredNode):
    """
    Map from UASTNode
    app/parser/usast/node.py
    """

    __label__ = "Node"
    uid: str = StringProperty(required=True, unique_index=True)  # type: ignore[assignment]

    file_node_uid: str = StringProperty()  # type: ignore[assignment]
    """UID of file node contain this node"""

    node_type: str = StringProperty()  # type: ignore[assignment]
    name: str | None = StringProperty()  # type: ignore[assignment]

    start_byte: int = IntegerProperty()  # type: ignore[assignment]
    end_byte: int = IntegerProperty()  # type: ignore[assignment]

    start_row: int = IntegerProperty()  # type: ignore[assignment]
    start_column: int = IntegerProperty()  # type: ignore[assignment]
    end_row: int = IntegerProperty()  # type: ignore[assignment]
    end_column: int = IntegerProperty()  # type: ignore[assignment]

    docstring: str | None = StringProperty()  # type: ignore[assignment]

    metadata: dict | None = JSONProperty()  # type: ignore[assignment]

    children: RelationshipManager = RelationshipTo("UASTNodeModel", "PARENT_OF")  # type: ignore[assignment]
    parent: RelationshipManager = RelationshipFrom("UASTNodeModel", "PARENT_OF")  # type: ignore[assignment]

    # call graph edges, written by app/graph/build.py
    references: RelationshipManager = RelationshipTo("UASTNodeModel", "REFERENCE_TO")  # type: ignore[assignment]
    referenced_by: RelationshipManager = RelationshipFrom(  # type: ignore[assignment]
        "UASTNodeModel", "REFERENCE_TO"
    )

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        return {
            "uid": uast_node.id,
            "node_type": uast_node.node_type,
            "name": uast_node.name,
            "start_byte": uast_node.start_byte,
            "end_byte": uast_node.end_byte,
            "start_row": uast_node.start_point[0],
            "start_column": uast_node.start_point[1],
            "end_row": uast_node.end_point[0],
            "end_column": uast_node.end_point[1],
            "docstring": uast_node.docstring,
            "metadata": uast_node.metadata,
        }

    @classmethod
    def from_uast(cls, uast_node: UASTNode) -> Self:
        """
        This method not build recursive children and relationship.
        Args:
            uast_node: UASTNode
        Returns:
            Instance of This class
        """
        return cls(**cls.extract_kwargs(uast_node))


class DefinitionNodeModel(UASTNodeModel):
    __label__ = "Definition"

    visibility: str = StringProperty()  # type: ignore[assignment]
    modifiers: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    decorators: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, DefinitionNode)
        return super().extract_kwargs(uast_node) | {
            "visibility": uast_node.visibility,
            "modifiers": uast_node.modifiers,
            "decorators": uast_node.decorators,
        }

    def __init__(self, *args: Any, **kwargs: Any):
        if type(self) is DefinitionNodeModel:
            raise TypeError("DefinitionNodeModel is an abstract class")

        super().__init__(*args, **kwargs)


class TypeDefinitionNodeModel(DefinitionNodeModel):
    __label__ = "TypeDefinition"

    kind: str = StringProperty()  # type: ignore[assignment]
    base_types: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    enum_values: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    is_abstract: bool = BooleanProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, TypeDefinitionNode)
        return super().extract_kwargs(uast_node) | {
            "kind": uast_node.kind,
            "base_types": uast_node.base_types,
            "enum_values": uast_node.enum_values,
            "is_abstract": uast_node.is_abstract,
        }


class FunctionNodeModel(DefinitionNodeModel):
    __label__ = "Function"

    kind: str = StringProperty()  # type: ignore[assignment]
    return_type: str = StringProperty()  # type: ignore[assignment]
    is_async: bool = BooleanProperty()  # type: ignore[assignment]
    is_generator: bool = BooleanProperty()  # type: ignore[assignment]
    is_static: bool = BooleanProperty()  # type: ignore[assignment]
    is_abstract: bool = BooleanProperty()  # type: ignore[assignment]
    is_override: bool = BooleanProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, FunctionNode)
        return super().extract_kwargs(uast_node) | {
            "kind": uast_node.kind,
            "return_type": uast_node.return_type,
            "is_async": uast_node.is_async,
            "is_generator": uast_node.is_generator,
            "is_static": uast_node.is_static,
            "is_abstract": uast_node.is_abstract,
            "is_override": uast_node.is_override,
        }


class VariableNodeModel(DefinitionNodeModel):
    __label__ = "Variable"

    kind: str = StringProperty(required=True)  # type: ignore[assignment]

    data_type: str | None = StringProperty()  # type: ignore[assignment]
    initial_value: str | None = StringProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, VariableNode)
        return super().extract_kwargs(uast_node) | {
            "kind": uast_node.kind,
            "data_type": uast_node.data_type,
            "initial_value": uast_node.initial_value,
        }


class DependencyNodeModel(UASTNodeModel):
    __label__ = "Dependency"

    def __init__(self, *args: Any, **kwargs: Any):
        if type(self) is DependencyNodeModel:
            raise TypeError("DependencyNodeModel is an abstract class")
        super().__init__(*args, **kwargs)


class ImportNodeModel(DependencyNodeModel):
    __label__ = "Import"

    module_path: str = StringProperty()  # type: ignore[assignment]
    imported_names: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    alias: dict[str, str] = JSONProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, ImportNode)
        return super().extract_kwargs(uast_node) | {
            "module_path": uast_node.module_path,
            "imported_names": uast_node.imported_names,
            "alias": uast_node.alias,
        }


class ExportNodeModel(DependencyNodeModel):
    __label__ = "Export"

    exported_names: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    alias: dict[str, str] = JSONProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, ExportNode)
        return super().extract_kwargs(uast_node) | {
            "exported_names": uast_node.exported_names,
            "alias": uast_node.alias,
        }


class ReferenceNodeModel(UASTNodeModel):
    __label__ = "Reference"

    def __init__(self, *args: Any, **kwargs: Any):
        if type(self) is ReferenceNodeModel:
            raise TypeError("ReferenceNodeModel is an abstract class")
        super().__init__(*args, **kwargs)


class CallNodeModel(ReferenceNodeModel):
    __label__ = "Call"

    subject: str | None = StringProperty()  # type: ignore[assignment]

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, CallNode)
        return super().extract_kwargs(uast_node) | {
            "subject": uast_node.subject,
        }


class AttributeAccessNodeModel(ReferenceNodeModel):
    __label__ = "AttributeAccess"


class TypeReferenceNodeModel(ReferenceNodeModel):
    __label__ = "TypeReference"

    namespace: str = StringProperty()  # type: ignore[assignment]

    type_arguments: list[str] = ArrayProperty(StringProperty())  # type: ignore[assignment]
    """For generic type"""

    @classmethod
    def extract_kwargs(cls, uast_node: UASTNode) -> dict:
        assert isinstance(uast_node, TypeReferenceNode)
        return super().extract_kwargs(uast_node) | {
            "namespace": uast_node.namespace,
            "type_arguments": uast_node.type_arguments,
        }


type UAST_NODE_MODEL_TYPE = (
    UASTNodeModel
    | DefinitionNodeModel
    | TypeDefinitionNodeModel
    | FunctionNodeModel
    | VariableNodeModel
    | DependencyNodeModel
    | ImportNodeModel
    | ExportNodeModel
    | ReferenceNodeModel
    | CallNodeModel
    | AttributeAccessNodeModel
    | TypeReferenceNodeModel
)

_MODEL_BY_NODE_TYPE: dict[type[UASTNode], type[UAST_NODE_MODEL_TYPE]] = {
    TypeDefinitionNode: TypeDefinitionNodeModel,
    FunctionNode: FunctionNodeModel,
    VariableNode: VariableNodeModel,
    ImportNode: ImportNodeModel,
    ExportNode: ExportNodeModel,
    CallNode: CallNodeModel,
    AttributeAccessNode: AttributeAccessNodeModel,
    TypeReferenceNode: TypeReferenceNodeModel,
}


def get_model_cls_for_uast_node(uast_node: UASTNode) -> type[UAST_NODE_MODEL_TYPE]:
    """
    Get Model class for uast node.
    Args:
        uast_node:

    Returns:
        type of Neo4jModel
    """
    return _MODEL_BY_NODE_TYPE[type(uast_node)]
