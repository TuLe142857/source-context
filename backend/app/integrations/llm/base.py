from abc import ABC, abstractmethod
from typing import ClassVar, Literal, TypedDict

from .exception import LLMError


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class BaseLLMClient(ABC):
    provider: ClassVar[str]

    def __init__(self, model: str):
        self._model = model

    @property
    def model(self) -> str:
        """LLM model"""
        return self._model

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send one chat turn and return the stripped reply text.

        `max_tokens` and `temperature` are left to the provider default when None.

        Raises:
            LLMError: The provider call failed.
        """
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            content = self._complete(
                messages, max_tokens=max_tokens, temperature=temperature
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                f"{self.provider}/{self.model} chat failed: "
                f"{exc.__class__.__name__}: {exc}"
            ) from exc
        return (content or "").strip()

    @abstractmethod
    def _complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None,
        temperature: float | None,
    ) -> str | None:
        """Send one request to the provider. Use chat() instead."""
