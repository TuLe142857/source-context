"""OpenAI inference client and wrapper implementing BaseInference."""

from collections.abc import Iterator
from functools import lru_cache
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.embedding.base import BaseInference, build_summary_prompts
from app.parser.uast.node import UASTNode

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_openai_client(api_key: str | None = None) -> OpenAI | None:
    """Loads and caches the OpenAI client instance.

    Args:
        api_key (str | None, optional): Custom OpenAI API Key. Defaults to None.

    Returns:
        OpenAI | None: Initialized OpenAI client instance or None if API key is not configured.
    """
    key = api_key or settings.OPENAI_API_KEY.get_secret_value()
    base_url = settings.OPENAI_API_BASE_URL
    if not key or key.strip() == "":
        return None

    return OpenAI(api_key=key, base_url=base_url)


class OpenAIInference(BaseInference):
    """OpenAI API inference implementation of BaseInference for code summarization and LLM interaction."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initializes the OpenAI inference service.

        Args:
            api_key (str | None, optional): Custom OpenAI API Key. Defaults to None.
            base_url (str | None, optional): Custom API Base URL. Defaults to None.
            model (str | None, optional): Default OpenAI model. Defaults to None.
            client (OpenAI | None, optional): Existing OpenAI client instance. Defaults to None.
        """
        self.api_key: str | None = api_key
        self.base_url: str | None = base_url
        self.model: str = model or settings.OPENAI_MODEL or "gpt-4o-mini"
        self._client: OpenAI | None = (
            client if client is not None else get_openai_client(api_key=self.api_key)
        )

    @property
    def client(self) -> OpenAI:
        """Returns the initialized OpenAI client instance.

        Raises:
            RuntimeError: If OpenAI API client is not configured.
        """
        if self._client is None:
            self._client = get_openai_client(api_key=self.api_key)
        if self._client is None:
            raise RuntimeError(
                "OpenAI API client is not initialized. Please ensure OPENAI_API_KEY is set in environment or config."
            )
        return self._client

    def get_summary(
        self,
        root_node: UASTNode,
        target_node: UASTNode,
        file_path: str | Path,
        signature: str,
        max_tokens: int = 600,
        temperature: float = 0.3,
    ) -> str:
        """Generates a high-precision, non-generic LLM summary for a code construct using OpenAI.

        Args:
            root_node (UASTNode): Root UAST container node of the file.
            target_node (UASTNode): Target FunctionNode or TypeDefinitionNode to summarize.
            file_path (str | Path): File path of the source code.
            signature (str): Extracted function or class signature.
            max_tokens (int, optional): Maximum generated tokens. Defaults to 600.
            temperature (float, optional): Sampling temperature. Defaults to 0.3.

        Returns:
            str: English semantic summary text.
        """
        system_prompt, user_prompt = build_summary_prompts(
            root_node=root_node,
            target_node=target_node,
            file_path=file_path,
            signature=signature,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Executes a chat completion call and returns the text response.

        Args:
            messages (list[dict[str, Any]]): Messages history.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 512.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.

        Returns:
            str: Generated assistant reply text.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Iterator[str]:
        """Streams assistant response chunks for a list of messages.

        Args:
            messages (list[dict[str, Any]]): Messages history.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 512.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.

        Yields:
            str: Generated delta token strings.
        """
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            content = getattr(chunk, "choices", [None])[0]
            if (
                content
                and hasattr(content, "delta")
                and getattr(content.delta, "content", None)
            ):
                text = content.delta.content
                if text:
                    yield text


@lru_cache(maxsize=1)
def get_openai_inference(
    api_key: str | None = None,
    model: str | None = None,
) -> OpenAIInference:
    """Returns a cached OpenAIInference instance.

    Args:
        api_key (str | None, optional): Custom OpenAI API Key. Defaults to None.
        model (str | None, optional): OpenAI model name. Defaults to None.

    Returns:
        OpenAIInference: Initialized OpenAIInference instance.
    """
    return OpenAIInference(api_key=api_key, model=model)
