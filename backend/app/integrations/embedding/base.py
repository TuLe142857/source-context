from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Sequence


class BaseEmbedder(ABC):
    provider: ClassVar[str]

    def __init__(self, dimensions: int, model: str):
        self._dimensions = dimensions
        self._model = model

    @property
    def dimensions(self) -> int:
        """Output dimensions of the embedder."""
        return self._dimensions

    @property
    def model(self) -> str:
        """Embedding model"""
        return self._model

    def embed_documents(self, texts: list[str]) -> Sequence[Sequence[float]]:
        return self.embed(texts, "document")

    def embed_query(self, text: str) -> Sequence[Sequence[float]]:
        return self.embed([text], "query")

    @abstractmethod
    def embed(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> Sequence[Sequence[float]]:
        pass
