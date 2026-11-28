from typing import Literal, Sequence

from ollama import Client

from .base import BaseEmbedder


class OllamaEmbedder(BaseEmbedder):
    provider = "ollama"

    def __init__(
        self,
        dimensions: int,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        batch_size: int = 64,
        timeout: float | None = 60.0,
    ):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = Client(host=base_url, headers=headers, timeout=timeout)

        super().__init__(dimensions, model, batch_size=batch_size)

    def embed(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> Sequence[Sequence[float]]:
        res = self._client.embed(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return res.embeddings
