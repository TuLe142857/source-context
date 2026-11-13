import hashlib
import io
from contextlib import nullcontext
from pathlib import Path

from neomodel import db

from app.core.config import settings
from app.core.s3 import get_s3_client
from app.engine.parser.uast import (
    ContainerNode,
    UASTNode,
)

from .model import (
    FileNodeModel,
    ProjectNodeModel,
    UASTNodeModel,
    get_model_cls_for_uast_node,
)


def save_file_node(
    uast_root: UASTNode,
    project_id: int,
    source_bytes: bytes | None = None,
    file_ext: str | None = None,
    *,
    transactional: bool = True,
) -> FileNodeModel:
    """

    Args:
        uast_root: UAST container node for one source file (`kind == "file"`).
        project_id:
        source_bytes: source file as bytes or none. Only upload file if bytes is not None or empty.
        file_ext: file extension, use to generate s3 key with file extension. Extension must include dot
    Returns:
        The persisted `FileNodeModel` for this file.

    Raises:
        ValueError: If `uast_root.kind` is not `"file"`.
    """
    if not isinstance(uast_root, ContainerNode):
        raise ValueError("Expected `ContainerNode` for `uast_root`")

    if uast_root.kind != "file":
        raise ValueError(
            f"build_graph_for_file expects a container node with kind='file', "
            f"got kind={uast_root.kind!r}"
        )

    if (source_bytes is not None) and (len(source_bytes) > 0):
        file_identity = uast_root.path or uast_root.name or "unknown"
        path_hash = hashlib.sha256(file_identity.encode("utf-8")).hexdigest()
        content_hash = hashlib.sha256(source_bytes).hexdigest()
        source_code_key = (
            f"source_code_file/project_{project_id}/{path_hash}/"
            f"{content_hash}{file_ext if file_ext else ''}"
        )

        source_byte_io = io.BytesIO(source_bytes)
        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            Fileobj=source_byte_io,
            Bucket=settings.S3_DEFAULT_BUCKET,
            Key=source_code_key,
        )
    else:
        source_code_key = None

    with (db.transaction if transactional else nullcontext()):
        project_node: ProjectNodeModel = ProjectNodeModel.nodes.get(uid=project_id)

        file_node: FileNodeModel = FileNodeModel(
            uid=uast_root.id,
            name=Path(uast_root.path).name if uast_root.path else uast_root.name,
            relative_path=uast_root.path,
            source_code_key=source_code_key,
        ).save()
        project_node.files.connect(file_node)
        for child in uast_root.children:
            child_node = _build_node_tree(child, file_node.uid)
            file_node.children.connect(child_node)

    return file_node


def _build_node_tree(node: UASTNode, file_node_uid: str) -> UASTNodeModel:
    """Recursively convert and save `node` and all of its descendants.

    Args:
        node: The UAST node to convert.

    Returns:
        The persisted model for `node`, already connected via `CHILDREN` to the
        (already persisted) models of its children.
    """
    model_cls = get_model_cls_for_uast_node(node)
    node_model: UASTNodeModel = model_cls.from_uast(node)
    node_model.file_node_uid = file_node_uid
    node_model.save()

    for child in node.children:
        child_model = _build_node_tree(child, file_node_uid)
        node_model.children.connect(child_model)

    return node_model
