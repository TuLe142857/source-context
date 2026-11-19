from typing import Literal, Sequence

from .base import BaseEmbedder
import voyageai

class VoyageEmbedder(BaseEmbedder):
    def __init__(self, dimension: int, model: str, base_url: str | None, api_key: str | None):
        self._client = voyageai.Client(base_url=base_url, api_key=api_key)
        super().__init__(dimension, model)

    def embed(self, texts: list[str], input_type: Literal["query", "document"]) -> Sequence[Sequence[float]]:
        res = self._client.embed(
            texts=texts,
            input_type=input_type,
            output_dimension=self.dimensions,
        )
        return res.embeddings