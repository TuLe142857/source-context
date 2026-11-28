from typing import cast

from openai import Client, omit
from openai.types.chat import ChatCompletionMessageParam

from .base import BaseLLMClient, ChatMessage


class OpenAILLMClient(BaseLLMClient):
    """Client for OpenAI and any OpenAI-compatible endpoint (e.g. ollama.com/v1)."""

    provider = "openai"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = 120.0,
        max_retries: int = 3,
    ):
        self._client = Client(
            api_key=api_key or None,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        super().__init__(model)

    def _complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None,
        temperature: float | None,
    ) -> str | None:
        # Unset params are omitted from the request (not sent as null): some
        # OpenAI-compatible servers reject parameters they do not know.
        res = self._client.chat.completions.create(
            model=self.model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            max_tokens=omit if max_tokens is None else max_tokens,
            temperature=omit if temperature is None else temperature,
        )
        if not res.choices:
            return None
        return res.choices[0].message.content
