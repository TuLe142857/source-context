from pathlib import Path

from neomodel import db

from app.parser.uast import (
    ContainerNode,
    UASTNode,
)

from .model import (
    ProjectNodeModel,
    FileNodeModel,
    UASTNodeModel,
    get_model_cls_for_uast_node,
)


def save_file_node(uast_root: ContainerNode, project_id: int) -> FileNodeModel:
    """
    Args:
        uast_root: UAST container node for one source file (`kind == "file"`).
        project_id:
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
        project_node: ProjectNodeModel = ProjectNodeModel.nodes.get(uid=project_id)

        file_node: FileNodeModel = FileNodeModel(
            uid=uast_root.id,
            name=Path(uast_root.path).name if uast_root.path else uast_root.name,
            relative_path=uast_root.path,
        ).save()
        project_node.files.connect(file_node)
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
    model_cls = get_model_cls_for_uast_node(node)
    node_model: UASTNodeModel = model_cls.from_uast(node).save()

    for child in node.children:
        child_model = _build_node_tree(child)
        node_model.children.connect(child_model)

    return node_model
