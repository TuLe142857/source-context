"""Unified inference module supporting interchangeable OpenAI and Local SLM (Phi-4-mini) providers."""

import logging
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

from app.core.config import settings
from app.embedding.base import BaseInference, build_summary_prompts
from app.embedding.local_slm_client import (
    LocalSLMInference,
    Phi4MiniInference,
    get_local_slm_client,
    get_local_summary,
)
from app.embedding.openai_client import (
    OpenAIInference,
    get_openai_client,
    get_openai_inference,
)
from app.parser.uast.node import UASTNode

logger = logging.getLogger(__name__)

InferenceProvider = Literal["openai", "local_slm"]


def get_inference_client(
    provider: InferenceProvider | str | None = None,
    **kwargs: Any,
) -> BaseInference:
    """Returns an initialized inference client based on provider ('openai' or 'local_slm').

    Args:
        provider (InferenceProvider | str | None, optional):
            Provider name. Defaults to settings.LLM_PROVIDER ('openai' or 'local_slm').
        **kwargs (Any): Additional configuration parameters passed to the client initializer.

    Returns:
        BaseInference: An initialized inference client implementing BaseInference.

    Raises:
        ValueError: If an unsupported provider is requested.
    """
    selected = (provider if provider is not None else settings.LLM_PROVIDER).lower()
    if selected == "local_slm":
        return get_local_slm_client(**kwargs)
    if selected == "openai":
        return get_openai_inference(**kwargs)
    raise ValueError(
        f"Unsupported inference provider '{provider}'. Expected 'openai' or 'local_slm'."
    )


def get_summary(
    root_node: UASTNode,
    target_node: UASTNode,
    file_path: str | Path,
    signature: str,
    client: BaseInference | OpenAI | None = None,
    model: str = "gpt-4o-mini",
    provider: InferenceProvider | str | None = None,
) -> str:
    """Generates a high-precision, non-generic LLM semantic summary for a code construct.

    Seamlessly supports both OpenAI and Local SLM providers.

    Args:
        root_node (UASTNode): Root UAST container node of the file.
        target_node (UASTNode): Target FunctionNode or TypeDefinitionNode to summarize.
        file_path (str | Path): File path of the source code.
        signature (str): Extracted function or class signature.
        client (BaseInference | OpenAI | None, optional): Custom client instance.
            If BaseInference (OpenAIInference or LocalSLMInference), delegates directly.
            If OpenAI instance, uses OpenAIInference.
            If None, resolves client via `provider` or `settings.LLM_PROVIDER`.
        model (str, optional): Target model name for OpenAI (defaults to 'gpt-4o-mini').
        provider (InferenceProvider | str | None, optional): Specific provider ('openai' or 'local_slm').

    Returns:
        str: English semantic summary formatted for Vector Search indexing.
    """
    if isinstance(client, BaseInference):
        return client.get_summary(
            root_node=root_node,
            target_node=target_node,
            file_path=file_path,
            signature=signature,
        )

    if isinstance(client, OpenAI):
        openai_inf = OpenAIInference(client=client, model=model)
        return openai_inf.get_summary(
            root_node=root_node,
            target_node=target_node,
            file_path=file_path,
            signature=signature,
        )

    inf_client = get_inference_client(provider=provider)
    return inf_client.get_summary(
        root_node=root_node,
        target_node=target_node,
        file_path=file_path,
        signature=signature,
    )


# Backward compatibility aliases
summarize_code_node = get_summary
get_llm_model = get_openai_client

__all__ = [
    "BaseInference",
    "InferenceProvider",
    "LocalSLMInference",
    "OpenAIInference",
    "Phi4MiniInference",
    "build_summary_prompts",
    "get_inference_client",
    "get_llm_model",
    "get_local_slm_client",
    "get_local_summary",
    "get_openai_client",
    "get_openai_inference",
    "get_summary",
    "summarize_code_node",
]


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    current_provider = settings.LLM_PROVIDER
    print(f"Initializing inference client (provider: {current_provider})...")

    try:
        active_client = get_inference_client()
        print(f"Client initialized successfully: {active_client.__class__.__name__}")
    except Exception as exc:
        print(f"Error initializing default client: {exc}")
        print("Falling back to local SLM...")
        active_client = get_inference_client(provider="local_slm")

    print("Type 'exit' or 'quit' to exit.")
    print("-" * 50)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "You are a helpful, smart AI assistant. Answer concisely and accurately in English.",
        }
    ]

    while True:
        try:
            user_input = input("\nUser: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        print("\nAI: ", end="", flush=True)

        reply = ""
        for chunk in active_client.stream_chat(messages):
            reply += chunk
            print(chunk, end="", flush=True)
        print()

        messages.append({"role": "assistant", "content": reply})
        if len(messages) > 20:
            messages = [messages[0]] + messages[-19:]
