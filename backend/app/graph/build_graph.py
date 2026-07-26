from pathlib import Path

from neomodel import db

from app.parser.uast import (
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

from .model import (
    AttributeAccessNodeModel,
    CallNodeModel,
    ExportNodeModel,
    FileNodeModel,
    FunctionNodeModel,
    ImportNodeModel,
    TypeDefinitionNodeModel,
    TypeReferenceNodeModel,
    UASTNodeModel,
    VariableNodeModel,
)

_MODEL_BY_NODE_TYPE: dict[type[UASTNode], type[UASTNodeModel]] = {
    TypeDefinitionNode: TypeDefinitionNodeModel,
    FunctionNode: FunctionNodeModel,
    VariableNode: VariableNodeModel,
    ImportNode: ImportNodeModel,
    ExportNode: ExportNodeModel,
    CallNode: CallNodeModel,
    AttributeAccessNode: AttributeAccessNodeModel,
    TypeReferenceNode: TypeReferenceNodeModel,
}


def build_graph_for_file(uast_root: ContainerNode) -> FileNodeModel:
    """Persist one file's UAST tree as a `File` node plus its UAST node subtree.

    Creates a `FileNodeModel` for `uast_root`, then recursively converts every
    descendant `UASTNode` into the matching `UASTNodeModel` subclass via
    `UASTNodeModel.from_uast`. Top-level UAST nodes are linked to the file via
    `DECLARE`; every other parent/child pair is linked via `CHILDREN`. The whole
    subtree is written in a single transaction so a failure partway through
    does not leave partial data.

    Args:
        uast_root: UAST container node for one source file (`kind == "file"`).

    Returns:
        The persisted `FileNodeModel` for this file.

    Raises:
        ValueError: If `uast_root.kind` is not `"file"`.
    """
    if uast_root.kind != "file":
        raise ValueError(
            f"build_graph_for_file expects a container node with kind='file', "
            f"got kind={uast_root.kind!r}"
        )

    with db.transaction:
        file_node: FileNodeModel = FileNodeModel(
            uid=uast_root.id,
            name=Path(uast_root.path).name if uast_root.path else uast_root.name,
            relative_path=uast_root.path,
        ).save()

        for child in uast_root.children:
            child_node = _build_node_tree(child)
            file_node.nodes.connect(child_node)

    return file_node


def _build_node_tree(node: UASTNode) -> UASTNodeModel:
    """Recursively convert and save `node` and all of its descendants.

    Args:
        node: The UAST node to convert.

    Returns:
        The persisted model for `node`, already connected via `CHILDREN` to the
        (already persisted) models of its children.
    """
    model_cls = _MODEL_BY_NODE_TYPE.get(type(node), UASTNodeModel)
    node_model: UASTNodeModel = model_cls.from_uast(node).save()

    for child in node.children:
        child_model = _build_node_tree(child)
        node_model.children.connect(child_model)

    return node_model
