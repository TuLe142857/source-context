"""Voyage AI embedding client wrapper for voyage-code-3."""

from functools import lru_cache
import logging
from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    from app.core.qdrant import QdrantVectorStore
    from app.embedding.utils import EnrichedNodeData

logger = logging.getLogger(__name__)

try:
    import voyageai

    HAS_VOYAGE = True
except ImportError:
    HAS_VOYAGE = False
    voyageai = None  # type: ignore[assignment]


class VoyageEmbedder:
    """Voyage AI embedding wrapper for voyage-code-3."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        vector_dim: int = 1024,
    ) -> None:
        """Initializes Voyage AI client.

        Args:
            api_key (str | None): Custom Voyage AI API Key.
            model (str | None): Custom Voyage AI model (defaults to voyage-code-3).
            vector_dim (int): Expected vector dimension (defaults to 1024 for voyage-code-3).
        """
        self.api_key = api_key or settings.VOYAGE_API_KEY.get_secret_value()
        self.model = model or settings.VOYAGE_EMBEDDING_MODEL or "voyage-code-3"
        self.vector_dim = vector_dim

        self.client: Any = None
        if HAS_VOYAGE and self.api_key and self.api_key.strip():
            try:
                self.client = voyageai.Client(api_key=self.api_key)
                logger.info("Voyage AI Client initialized with model: %s", self.model)
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Voyage AI client: %s. Using mock fallback embedder.",
                    exc,
                )

    def is_available(self) -> bool:
        """Checks if real Voyage AI API client is initialized."""
        return self.client is not None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a list of document code chunks using input_type="document".

        Args:
            texts (list[str]): List of structured code text chunks.

        Returns:
            list[list[float]]: List of 1024-dimensional embedding vectors.
        """
        if not texts:
            return []

        if self.client is not None:
            try:
                res = self.client.embed(
                    texts=texts,
                    model=self.model,
                    input_type="document",
                )
                return res.embeddings  # type: ignore[no-any-return]
            except Exception as exc:
                logger.error(
                    "Error calling Voyage AI embed_documents: %s. Returning fallback mock vectors.",
                    exc,
                )

        # Fallback deterministic pseudo-random mock vectors (1024 dim) for demo/offline mode
        import math
        import random

        mock_vectors: list[list[float]] = []
        for text in texts:
            rng = random.Random(text)
            vec = [rng.uniform(-1.0, 1.0) for _ in range(self.vector_dim)]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            mock_vectors.append([x / norm for x in vec])
        return mock_vectors

    def embed_query(self, query: str) -> list[float]:
        """Embeds a search query prompt using input_type="query".

        Args:
            query (str): Natural language search query string.

        Returns:
            list[float]: 1024-dimensional embedding vector.
        """
        if self.client is not None:
            try:
                res = self.client.embed(
                    texts=[query],
                    model=self.model,
                    input_type="query",
                )
                return res.embeddings[0]  # type: ignore[no-any-return]
            except Exception as exc:
                logger.error(
                    "Error calling Voyage AI embed_query: %s. Returning fallback mock vector.",
                    exc,
                )

        import math
        import random

        rng = random.Random(query)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(self.vector_dim)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


@lru_cache(maxsize=1)
def get_voyage_embedder() -> VoyageEmbedder:
    """Returns a cached instance of VoyageEmbedder."""
    return VoyageEmbedder()


def batch_embed_nodes_template(
    enhanced_batch: list["EnrichedNodeData"],
    vector_store: "QdrantVectorStore | None" = None,
) -> list["EnrichedNodeData"]:
    """Embeds enriched node chunks with Voyage AI (voyage-code-3) and upserts vector points to Qdrant.

    Args:
        enhanced_batch (list[EnrichedNodeData]): Batch of enriched nodes with structured text.
        vector_store (QdrantVectorStore | None): Optional target QdrantVectorStore instance.

    Returns:
        list[EnrichedNodeData]: Enriched nodes with vector embeddings populated.
    """
    if not enhanced_batch:
        return []

    from app.core.qdrant import QdrantVectorStore

    embedder = get_voyage_embedder()
    store = vector_store or QdrantVectorStore()

    texts = [
        item.formatted_embed_text or item.summary or item.signature
        for item in enhanced_batch
    ]

    embeddings = embedder.embed_documents(texts)
    for idx, item in enumerate(enhanced_batch):
        if idx < len(embeddings):
            item.embedding = embeddings[idx]

    store.upsert_batch(enhanced_batch, vector_size=1024)
    return enhanced_batch
