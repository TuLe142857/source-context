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
print(settings.NEO4J_URI)


class WorkspaceNodeModel(StructuredNode):
    __label__ = "Workspace"

    uid = IntegerProperty(required=True, unique_index=True)
    name = StringProperty(required=True)

    repositories: RelationshipManager = RelationshipTo(  # type: ignore[assignment]
        "RepositoryNodeModel", "INCLUDES"
    )


class RepositoryNodeModel(StructuredNode):
    __label__ = "Repository"

    uid = IntegerProperty(required=True, unique_index=True)
    name = StringProperty()

    branches: RelationshipManager = RelationshipTo("BranchNodeModel", "INCLUDES")  # type: ignore[assignment]

    workspace: RelationshipManager = RelationshipFrom("WorkspaceNodeModel", "INCLUDES")  # type: ignore[assignment]


class BranchNodeModel(StructuredNode):
    __label__ = "Branch"

    uid = IntegerProperty(required=True, unique_index=True)
    name = StringProperty()
    commit_hash = StringProperty()


class ProjectNodeModel(StructuredNode):
    __label__ = "Project"

    uid = StringProperty(required=True, unique_index=True)

    name = StringProperty()

    commit_hash = StringProperty()
    """Commit hash of this branch"""

    relative_path = StringProperty()
    """path from repository root"""

    files: RelationshipManager = RelationshipTo("FileNodeModel", "INCLUDES")  # type: ignore[assignment]
    branch: RelationshipManager = RelationshipFrom("BranchNodeModel", "INCLUDES")  # type: ignore[assignment]


class FileNodeModel(StructuredNode):
    __label__ = "File"

    uid = StringProperty(required=True, unique_index=True)

    name = StringProperty()
    """file name"""

    relative_path = StringProperty()
    """path from project root"""

    nodes: RelationshipManager = RelationshipTo("UASTNodeModel", "DECLARE")  # type: ignore[assignment]

    project: RelationshipManager = RelationshipFrom("ProjectNodeModel", "INCLUDES")  # type: ignore[assignment]


class UASTNodeModel(StructuredNode):
    """
    Map from UASTNode
    app/parser/usast/node.py
    """

    __label__ = "Node"
    uid = StringProperty(required=True, unique_index=True)

    node_type = StringProperty()
    name = StringProperty()

    start_byte = IntegerProperty()
    end_byte = IntegerProperty()

    start_row = IntegerProperty()
    start_column = IntegerProperty()
    end_row = IntegerProperty()
    end_column = IntegerProperty()

    docstring = StringProperty()

    metadata = JSONProperty()

    children: RelationshipManager = RelationshipTo("UASTNodeModel", "PARENT_OF")  # type: ignore[assignment]
    parent: RelationshipManager = RelationshipFrom("UASTNodeModel", "PARENT_OF")  # type: ignore[assignment]

    # for future when implement call graph cross file
    references = RelationshipTo("UASTNodeModel", "REFERENCE_TO")
    referenced_by = RelationshipFrom("UASTNodeModel", "REFERENCE_TO")

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

    visibility = StringProperty()
    modifiers = ArrayProperty(StringProperty())
    decorators = ArrayProperty(StringProperty())

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

    kind = StringProperty()
    base_types = ArrayProperty(StringProperty())
    enum_values = ArrayProperty(StringProperty())
    is_abstract = BooleanProperty()

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

    kind = StringProperty()
    return_type = StringProperty()
    is_async = BooleanProperty()
    is_generator = BooleanProperty()
    is_static = BooleanProperty()
    is_abstract = BooleanProperty()
    is_override = BooleanProperty()

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

    kind = StringProperty(required=True)

    data_type = StringProperty()
    initial_value = StringProperty()

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

    module_path = StringProperty()
    imported_names = ArrayProperty(StringProperty())
    alias = JSONProperty()

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
    exported_names = ArrayProperty(StringProperty())
    alias = JSONProperty()

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

    subject = StringProperty()

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

    namespace = StringProperty()

    type_arguments = ArrayProperty(StringProperty())
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
