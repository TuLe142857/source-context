"""CodeRetriever service class for top-k natural language semantic code search."""

from dataclasses import dataclass
import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.qdrant import get_qdrant_client
from app.embedding.voyage_embedder import VoyageEmbedder, get_voyage_embedder

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueryResult:
    """Dataclass holding a single search result hit from Qdrant."""

    score: float
    name: str
    kind: str
    file_path: str
    signature: str
    summary: str | None
    docstring: str | None
    identifiers: list[str]
    formatted_embed_text: str | None
    payload: dict[str, Any]
    branch_id: int | None = None


class CodeRetriever:
    """Retrieval service for natural language code search using Voyage AI and Qdrant."""

    def __init__(
        self,
        embedder: VoyageEmbedder | None = None,
        client: QdrantClient | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initializes CodeRetriever.

        Args:
            embedder (VoyageEmbedder | None): Optional VoyageEmbedder instance.
            client (QdrantClient | None): Optional QdrantClient instance (defaults to singleton).
            collection_name (str | None): Target Qdrant collection name.
        """
        self.embedder = embedder or get_voyage_embedder()
        self.client = client or get_qdrant_client()
        self.collection_name = (
            collection_name or settings.QDRANT_COLLECTION_NAME or "code_chunks"
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        branch_id: int | None = None,
    ) -> list[QueryResult]:
        """Embeds natural language search query with Voyage AI and retrieves top-k results from Qdrant.

        Args:
            query (str): Natural language search prompt/query.
            top_k (int): Number of top search results to return (default 5).
            branch_id (int | None): Optional target branch ID filter.

        Returns:
            list[QueryResult]: Ordered list of top-k search results with similarity scores.
        """
        if not query or not query.strip():
            return []

        logger.info(
            "Searching Qdrant collection '%s' for query: '%s' (top_k=%d, branch_id=%s)...",
            self.collection_name,
            query,
            top_k,
            branch_id,
        )

        # 1. Embed search query using Voyage AI input_type="query"
        query_vector = self.embedder.embed_query(query)

        # 2. Build filter if branch_id is specified
        query_filter = None
        if branch_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="branch_id",
                        match=MatchValue(value=branch_id),
                    )
                ]
            )

        # 3. Search Qdrant collection for top-k nearest vector hits
        try:
            if hasattr(self.client, "query_points"):
                query_res = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
                hits = query_res.points
            else:
                hits = getattr(self.client, "search")(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                )
        except Exception as exc:
            logger.error(
                "Error querying Qdrant collection '%s': %s",
                self.collection_name,
                exc,
            )
            return []

        results: list[QueryResult] = []
        for hit in hits:
            payload = hit.payload or {}
            res = QueryResult(
                score=float(hit.score),
                name=payload.get("name", "unnamed"),
                kind=payload.get("kind", "unknown"),
                file_path=payload.get("file_path", ""),
                signature=payload.get("signature", ""),
                summary=payload.get("summary"),
                docstring=payload.get("docstring"),
                identifiers=payload.get("identifiers", []),
                formatted_embed_text=payload.get("formatted_embed_text"),
                payload=payload,
                branch_id=payload.get("branch_id"),
            )
            results.append(res)

        return results
