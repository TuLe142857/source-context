from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Sequence

from .exception import EmbeddingError


class BaseEmbedder(ABC):
    provider: ClassVar[str]

    def __init__(self, dimensions: int, model: str, batch_size: int = 64):
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        self._dimensions = dimensions
        self._model = model
        self._batch_size = batch_size

    @property
    def dimensions(self) -> int:
        """Output dimensions of the embedder."""
        return self._dimensions

    @property
    def model(self) -> str:
        """Embedding model"""
        return self._model

    @property
    def batch_size(self) -> int:
        """Maximum number of texts sent in one provider request."""
        return self._batch_size

    def embed_documents(self, texts: list[str]) -> list[Sequence[float]]:
        """Embed documents, splitting them into batches of `batch_size`.

        Raises:
            EmbeddingError: The provider call failed.
            EmbeddingDimensionMismatchError: The provider returned the wrong
                number of vectors or a vector of the wrong dimension.
        """
        vectors: list[Sequence[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            vectors.extend(self._embed_checked(batch, "document"))
        return vectors

    def embed_query(self, text: str) -> Sequence[float]:
        """Embed a single query and return its vector.

        Raises:
            EmbeddingError: The provider call failed.
            EmbeddingDimensionMismatchError: The provider returned a vector
                of the wrong dimension.
        """
        return self._embed_checked([text], "query")[0]

    def _embed_checked(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> list[Sequence[float]]:
        if not texts:
            return []
        try:
            vectors = list(self._embed(texts, input_type))
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                f"{self.provider}/{self.model} embed failed: "
                f"{exc.__class__.__name__}: {exc}"
            ) from exc
        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"{self.model} returned {len(vectors)} vectors for {len(texts)} texts"
            )
        for vector in vectors:
            if len(vector) != self._dimensions:
                raise EmbeddingError(
                    f"{self.model} returned a {len(vector)}-dimensional vector, "
                    f"expected {self._dimensions}"
                )
        return vectors

    @abstractmethod
    def _embed(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> Sequence[Sequence[float]]:
        """Send one request to the provider. Use embed_query or embed_document instead"""
