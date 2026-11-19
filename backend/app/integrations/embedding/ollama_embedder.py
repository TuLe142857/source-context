from .base import BaseEmbedder
from ollama import Client, AsyncClient

from typing import Sequence, Literal

class OllamaEmbedder(BaseEmbedder):
    def __init__(self, dimension: int, model: str, base_url: str | None = None, api_key: str | None = None):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key is not None else None
        self._client = Client(host=base_url, headers=headers)

        super().__init__(dimension, model)

    def embed(self, texts: list[str], input_type: Literal["query", "document"]) -> Sequence[Sequence[float]]:
        res = self._client.embed(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return res.embeddings