"""Qdrant client singleton factory and vector store management module."""

from functools import lru_cache
import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

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
        except Exception as exc:
            logger.warning(
                "Could not connect to Qdrant or verify collection '%s': %s",
                self.collection_name,
                exc,
            )

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

            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item.node_id))

            payload = {
                "branch_id": item.branch_id,
                "node_id": item.node_id,
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
        except Exception as exc:
            logger.error(
                "Failed to upsert points to Qdrant collection '%s': %s",
                self.collection_name,
                exc,
            )
            return 0
