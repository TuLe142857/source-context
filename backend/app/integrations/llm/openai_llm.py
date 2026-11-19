from .base import BaseLLMClient
from openai import Client
class OpenAILLMClient(BaseLLMClient):
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None):
        self._client = Client(api_key=api_key, base_url=base_url)
        super().__init__(model)

    def chat(self, message: str, system_prompt: str | None = None) -> str:
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
        else:
            messages = [{"role": "user", "content": message}]

        res = self._client.chat.completetions.create(
            model=self.model,
            messages=messages,
        )
        return res.choices[0].message.content

