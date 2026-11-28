from .base import BaseLLMClient
from ollama import Client


class OllamaLLMClient(BaseLLMClient):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = 120.0,
    ):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = Client(host=base_url, headers=headers, timeout=timeout)
        super().__init__(model)

    def chat(self, message: str, system_prompt: str | None = None) -> str:
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
        else:
            messages = [{"role": "user", "content": message}]

        res = self._client.chat(
            model=self.model,
            messages=messages,
        )
        return res.message.content or ""
