"""Qdrant client singleton factory and vector store management module."""

import json
import logging
import posixpath
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.embedding.utils import EnrichedNodeData

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Returns a cached, singleton instance of QdrantClient.

    Connects to the Qdrant Docker service configured in settings.
    Raises ConnectionError if the server is unreachable.
    """
    api_key = (
        settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None
    )
    if not api_key or api_key.strip() == "":
        api_key = None

    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        grpc_port=settings.QDRANT_GRPC_PORT,
        api_key=api_key,
        prefer_grpc=False,
    )

    # Test connectivity
    try:
        client.get_collections()
        return client
    except Exception as exc:
        logger.error(
            "Qdrant server not reachable at %s:%d. Error: %s",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
            exc,
        )
        raise ConnectionError(
            f"Could not connect to Qdrant server at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. "
            "Ensure the Qdrant Docker service is running."
        ) from exc


class QdrantVectorStore:
    """Manager class for Qdrant Vector Store indexing and point management."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initializes QdrantVectorStore using the singleton client by default.

        Args:
            client (QdrantClient | None): Optional custom QdrantClient.
            collection_name (str | None): Custom collection name (defaults to settings.QDRANT_COLLECTION_NAME).
        """
        self.client = client or get_qdrant_client()
        self.collection_name = (
            collection_name or settings.QDRANT_COLLECTION_NAME or "code_chunks"
        )

    def ensure_collection(self, vector_size: int = 1024) -> None:
        """Ensures that the target Qdrant collection exists with the specified vector dimension and Cosine distance.

        Args:
            vector_size (int): Vector dimension (defaults to 1024 for voyage-code-3).
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(
                    "Creating Qdrant collection '%s' (vector size: %d, Cosine distance)...",
                    self.collection_name,
                    vector_size,
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception:
            logger.exception(
                "Could not connect to Qdrant or verify collection '%s'",
                self.collection_name,
            )
            raise

    def upsert_batch(
        self,
        batch: list[EnrichedNodeData],
        vector_size: int = 1024,
    ) -> int:
        """Upserts a batch of EnrichedNodeData objects into Qdrant collection.

        Args:
            batch (list[EnrichedNodeData]): Enriched nodes containing embedding vectors and payload.
            vector_size (int): Vector dimension.

        Returns:
            int: Number of points successfully upserted.
        """
        if not batch:
            return 0

        self.ensure_collection(vector_size=vector_size)

        points: list[PointStruct] = []
        for item in batch:
            if not item.embedding:
                continue

            point_identity = json.dumps(
                [
                    "code-node-v3",
                    item.workspace_id,
                    item.branch_id,
                    item.project_id,
                    item.file_path.replace("\\", "/"),
                    item.node_type,
                    item.name,
                    item.signature,
                    item.start_byte,
                    item.end_byte,
                ],
                separators=(",", ":"),
            )
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, point_identity))

            payload = {
                "workspace_id": item.workspace_id,
                "branch_id": item.branch_id,
                "node_id": item.node_id,
                "project_id": item.project_id,
                "start_byte": item.start_byte,
                "end_byte": item.end_byte,
                "name": item.name,
                "kind": item.kind,
                "node_type": item.node_type,
                "file_path": item.file_path,
                "signature": item.signature,
                "docstring": item.docstring,
                "summary": item.summary,
                "identifiers": item.identifiers,
                "formatted_embed_text": item.formatted_embed_text,
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=item.embedding,
                    payload=payload,
                )
            )

        if not points:
            return 0

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            logger.info(
                "Successfully upserted %d points to Qdrant collection '%s'.",
                len(points),
                self.collection_name,
            )
            return len(points)
        except Exception:
            logger.exception(
                "Failed to upsert points to Qdrant collection '%s'",
                self.collection_name,
            )
            raise

    def delete_file(
        self,
        *,
        workspace_id: int,
        branch_id: int,
        file_path: str,
        project_id: int | None = None,
    ) -> None:
        """Delete points owned by one workspace, branch, and source file."""
        self.ensure_collection()
        conditions = [
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
            FieldCondition(key="branch_id", match=MatchValue(value=branch_id)),
            FieldCondition(key="file_path", match=MatchValue(value=file_path)),
        ]
        if project_id is not None:
            conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(
                    filter=Filter(must=conditions),
                ),
            )
        except Exception:
            logger.exception(
                "Failed to delete Qdrant points for workspace=%s branch=%s file=%s",
                workspace_id,
                branch_id,
                file_path,
            )
            raise

    def replace_file(
        self,
        items: list[EnrichedNodeData],
        *,
        workspace_id: int,
        branch_id: int,
        project_id: int,
        file_path: str,
        vector_size: int = 1024,
    ) -> int:
        """Upsert a file's current vectors, then remove obsolete vectors.

        The operation is retry-safe: if cleanup fails, the next call upserts the
        same deterministic IDs and repeats cleanup. The caller must not advance
        its indexing checkpoint unless this method returns successfully.
        """
        for item in items:
            if (
                item.workspace_id != workspace_id
                or item.branch_id != branch_id
                or item.project_id != project_id
                or item.file_path.replace("\\", "/") != file_path.replace("\\", "/")
            ):
                raise ValueError("All vectors must belong to the replacement target")

        if not items:
            self.ensure_collection(vector_size=vector_size)
        self.upsert_batch(items, vector_size=vector_size)
        expected_ids = {
            str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    json.dumps(
                        [
                            "code-node-v3",
                            item.workspace_id,
                            item.branch_id,
                            item.project_id,
                            item.file_path.replace("\\", "/"),
                            item.node_type,
                            item.name,
                            item.signature,
                            item.start_byte,
                            item.end_byte,
                        ],
                        separators=(",", ":"),
                    ),
                )
            )
            for item in items
            if item.embedding
        }
        target_filter = Filter(
            must=[
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
                FieldCondition(key="branch_id", match=MatchValue(value=branch_id)),
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="file_path", match=MatchValue(value=file_path)),
            ]
        )
        obsolete_ids: list[str] = []
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=target_filter,
                limit=256,
                with_payload=False,
                with_vectors=False,
                offset=offset,
            )
            obsolete_ids.extend(
                str(point.id) for point in points if str(point.id) not in expected_ids
            )
            if next_offset is None:
                break
            offset = next_offset
        if obsolete_ids:
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=obsolete_ids,
                )
            except Exception:
                logger.exception(
                    "Failed to remove obsolete Qdrant points for workspace=%s branch=%s project=%s file=%s",
                    workspace_id,
                    branch_id,
                    project_id,
                    file_path,
                )
                raise
        return len(expected_ids)

    def reconcile_project_files(
        self,
        *,
        workspace_id: int,
        branch_id: int,
        project_id: int,
        current_file_paths: set[str],
    ) -> None:
        """Remove vectors for files no longer present in a fully scanned project."""
        self.ensure_collection()
        project_filter = Filter(
            must=[
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
                FieldCondition(key="branch_id", match=MatchValue(value=branch_id)),
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
            ]
        )
        obsolete_ids: list[str] = []
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=project_filter,
                limit=256,
                with_payload=["file_path"],
                with_vectors=False,
                offset=offset,
            )
            obsolete_ids.extend(
                str(point.id)
                for point in points
                if (point.payload or {}).get("file_path") not in current_file_paths
            )
            if next_offset is None:
                break
            offset = next_offset
        if obsolete_ids:
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=obsolete_ids,
                )
            except Exception:
                logger.exception(
                    "Failed to remove stale Qdrant files for workspace=%s branch=%s project=%s",
                    workspace_id,
                    branch_id,
                    project_id,
                )
                raise

    def reconcile_legacy_points(
        self,
        *,
        workspace_id: int,
        branch_id: int,
        affected_paths: set[str] | None = None,
        project_roots: set[str] | None = None,
    ) -> None:
        """Retire attributable legacy points after a target's vectors are written.

        Legacy points without project_id are removed only when their exact file path
        changed, or when a successful full rebuild covered the containing project
        root. Records without enough target/path metadata are left untouched.
        """
        normalized_paths = {
            posixpath.normpath(path.replace("\\", "/"))
            for path in (affected_paths or set())
        }
        normalized_roots = {
            posixpath.normpath(root.replace("\\", "/")).rstrip("/")
            for root in (project_roots or set())
        }
        if not normalized_paths and not normalized_roots:
            return

        self.ensure_collection()
        target_filter = Filter(
            must=[
                FieldCondition(
                    key="workspace_id", match=MatchValue(value=workspace_id)
                ),
                FieldCondition(
                    key="branch_id", match=MatchValue(value=branch_id)
                ),
            ]
        )
        obsolete_ids: list[str] = []
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=target_filter,
                limit=256,
                with_payload=["project_id", "file_path"],
                with_vectors=False,
                offset=offset,
            )
            for point in points:
                payload = point.payload or {}
                path = posixpath.normpath(
                    str(payload.get("file_path") or "").replace("\\", "/")
                )
                if payload.get("project_id") is not None or not path:
                    continue
                in_rebuilt_root = any(
                    path == root or path.startswith(f"{root}/")
                    for root in normalized_roots
                )
                if path in normalized_paths or in_rebuilt_root:
                    obsolete_ids.append(str(point.id))
            if next_offset is None:
                break
            offset = next_offset

        if obsolete_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=obsolete_ids,
            )
