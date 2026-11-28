from typing import Literal, Sequence

import voyageai

from .base import BaseEmbedder


class VoyageEmbedder(BaseEmbedder):
    provider = "voyage"

    def __init__(
        self,
        dimensions: int,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        batch_size: int = 64,
        timeout: float | None = 60.0,
        max_retries: int = 3,
    ):
        self._client = voyageai.Client(
            api_key=api_key or None,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        super().__init__(dimensions, model, batch_size=batch_size)

    def _embed(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> Sequence[Sequence[float]]:
        res = self._client.embed(
            texts=texts,
            model=self.model,
            input_type=input_type,
            output_dimension=self.dimensions,
        )
        return res.embeddings
