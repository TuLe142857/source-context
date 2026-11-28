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
        query_prefix: str = "",
        document_prefix: str = "",
    ):
        """
        Args:
            query_prefix: Prepended to query texts. Some models need a task
                prefix, e.g. "search_query: " for nomic-embed-text.
            document_prefix: Prepended to document texts, e.g. "search_document: ".
        """
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = Client(host=base_url, headers=headers, timeout=timeout)
        self._query_prefix = query_prefix
        self._document_prefix = document_prefix

        super().__init__(dimensions, model, batch_size=batch_size)

    def _embed(
        self, texts: list[str], input_type: Literal["query", "document"]
    ) -> Sequence[Sequence[float]]:
        prefix = self._query_prefix if input_type == "query" else self._document_prefix
        if prefix:
            texts = [prefix + text for text in texts]
        res = self._client.embed(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return res.embeddings
