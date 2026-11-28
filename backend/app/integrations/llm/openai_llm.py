from openai import Client
from openai.types.chat import ChatCompletionMessageParam

from .base import BaseLLMClient


class OpenAILLMClient(BaseLLMClient):
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

    def chat(self, message: str, system_prompt: str | None = None) -> str:
        messages: list[ChatCompletionMessageParam]
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
        else:
            messages = [{"role": "user", "content": message}]

        res = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return res.choices[0].message.content or ""
