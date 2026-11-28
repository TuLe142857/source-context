from typing import Any

from ollama import Client

from .base import BaseLLMClient, ChatMessage


class OllamaLLMClient(BaseLLMClient):
    provider = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = 120.0,
        keep_alive: str | None = None,
    ):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = Client(host=base_url, headers=headers, timeout=timeout)
        self._keep_alive = keep_alive
        super().__init__(model)

    def _complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None,
        temperature: float | None,
    ) -> str | None:
        options: dict[str, Any] = {}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature

        res = self._client.chat(
            model=self.model,
            messages=messages,
            options=options or None,
            keep_alive=self._keep_alive,
        )
        return res.message.content
