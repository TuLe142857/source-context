"""Local SLM inference module using Phi-4-mini and llama-cpp-python implementing BaseInference."""

from collections.abc import Iterator
from functools import lru_cache
import logging
from pathlib import Path
import sys
from typing import Any, cast

from llama_cpp import Llama
from llama_cpp.llama_types import (
    ChatCompletionRequestMessage,
    CreateChatCompletionResponse,
    CreateChatCompletionStreamResponse,
)

from app.core.config import settings
from app.embedding.base import BaseInference, build_summary_prompts
from app.parser.uast.node import UASTNode

logger = logging.getLogger(__name__)


def resolve_model_path(model_path: str | Path | None = None) -> Path:
    """Resolves the GGUF model path against known project directories.

    Args:
        model_path (str | Path | None, optional): Explicit model path or None. Defaults to None.

    Returns:
        Path: Resolved existing path to the GGUF model file.

    Raises:
        FileNotFoundError: If the model file is not found.
    """
    default_name = "Phi-4-mini-instruct-Q4_K_M.gguf"
    same_dir_model = Path(__file__).resolve().parent / default_name

    if model_path is not None:
        p = Path(model_path)
        candidates = [
            p,
            Path.cwd() / p,
            Path.cwd() / "backend" / p,
            Path(__file__).resolve().parent / p.name,
        ]
        for cand in candidates:
            if cand.is_file():
                return cand.resolve()
        raise FileNotFoundError(f"Local SLM model file not found at: {model_path}")

    # Check configured path from settings
    configured = getattr(settings, "LOCAL_SLM_MODEL_PATH", None)
    if configured:
        p_conf = Path(configured)
        candidates = [
            p_conf,
            Path.cwd() / p_conf,
            Path.cwd() / "backend" / p_conf,
            Path(__file__).resolve().parent / p_conf.name,
        ]
        for cand in candidates:
            if cand.is_file():
                return cand.resolve()

    if same_dir_model.is_file():
        return same_dir_model.resolve()

    raise FileNotFoundError(
        f"Default local SLM model '{default_name}' not found at {same_dir_model}. "
        "Please provide a valid model path."
    )


class LocalSLMInference(BaseInference):
    """Local SLM inference service powered by Phi-4-mini and llama-cpp-python implementing BaseInference."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        n_ctx: int = 4096,
        n_threads: int | None = None,
        n_gpu_layers: int = 0,
        verbose: bool = False,
    ) -> None:
        """Initializes the local SLM model instance using llama-cpp-python.

        Args:
            model_path (str | Path | None, optional): Path to GGUF model file.
                Defaults to configured path or app/embedding/Phi-4-mini-instruct-Q4_K_M.gguf.
            n_ctx (int, optional): Context window size in tokens. Defaults to 4096.
            n_threads (int | None, optional): Number of CPU threads. Defaults to None.
            n_gpu_layers (int, optional): Number of layers to offload to GPU. Defaults to 0.
            verbose (bool, optional): Whether to enable verbose logs from llama-cpp. Defaults to False.
        """
        self.resolved_model_path: Path = resolve_model_path(model_path)
        self.n_ctx: int = n_ctx
        self.n_threads: int | None = n_threads
        self.n_gpu_layers: int = n_gpu_layers
        self.verbose: bool = verbose

        logger.info(
            "Initializing Local SLM Phi-4-mini from: %s (n_ctx=%d, n_gpu_layers=%d)",
            self.resolved_model_path,
            self.n_ctx,
            self.n_gpu_layers,
        )

        init_kwargs: dict[str, Any] = {
            "model_path": str(self.resolved_model_path),
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "verbose": self.verbose,
        }
        if self.n_threads is not None:
            init_kwargs["n_threads"] = self.n_threads

        self.llm = Llama(**init_kwargs)

    def get_summary(
        self,
        root_node: UASTNode,
        target_node: UASTNode,
        file_path: str | Path,
        signature: str,
        max_tokens: int = 600,
        temperature: float = 0.3,
    ) -> str:
        """Generates a high-precision, non-generic semantic summary for a code construct using Phi-4-mini.

        Args:
            root_node (UASTNode): Root UAST container node of the file.
            target_node (UASTNode): Target FunctionNode or TypeDefinitionNode to summarize.
            file_path (str | Path): File path of the source code.
            signature (str): Extracted function or class signature.
            max_tokens (int, optional): Maximum generated tokens. Defaults to 600.
            temperature (float, optional): Sampling temperature. Defaults to 0.3.

        Returns:
            str: English semantic summary formatted for Vector Search indexing.
        """
        system_prompt, user_prompt = build_summary_prompts(
            root_node=root_node,
            target_node=target_node,
            file_path=file_path,
            signature=signature,
        )

        messages = cast(
            list[ChatCompletionRequestMessage],
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        res = cast(
            CreateChatCompletionResponse,
            self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            ),
        )

        choice = res["choices"][0]
        content = choice["message"].get("content")
        return (content or "").strip()

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
        typed_messages = cast(list[ChatCompletionRequestMessage], messages)
        res = cast(
            CreateChatCompletionResponse,
            self.llm.create_chat_completion(
                messages=typed_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            ),
        )
        choice = res["choices"][0]
        content = choice["message"].get("content")
        return (content or "").strip()

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
        typed_messages = cast(list[ChatCompletionRequestMessage], messages)
        chunks = cast(
            Iterator[CreateChatCompletionStreamResponse],
            self.llm.create_chat_completion(
                messages=typed_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            ),
        )
        for chunk in chunks:
            choice = chunk["choices"][0]
            delta = choice.get("delta", {})
            content = delta.get("content")
            if content:
                yield str(content)


@lru_cache(maxsize=1)
def get_local_slm_client(
    model_path: str | Path | None = None,
    n_ctx: int = 4096,
    n_threads: int | None = None,
    n_gpu_layers: int = 0,
) -> LocalSLMInference:
    """Loads and caches the LocalSLMInference singleton instance.

    Args:
        model_path (str | Path | None, optional): Custom path to GGUF model file. Defaults to None.
        n_ctx (int, optional): Context window size in tokens. Defaults to 4096.
        n_threads (int | None, optional): Number of CPU threads. Defaults to None.
        n_gpu_layers (int, optional): Number of GPU layers to offload. Defaults to 0.

    Returns:
        LocalSLMInference: Initialized LocalSLMInference instance.
    """
    return LocalSLMInference(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
    )


def get_summary(
    root_node: UASTNode,
    target_node: UASTNode,
    file_path: str | Path,
    signature: str,
    client: LocalSLMInference | None = None,
    model: str = "phi-4-mini",
) -> str:
    """Generates a semantic summary for a code construct using local Phi-4-mini.

    Args:
        root_node (UASTNode): Root UAST container node of the file.
        target_node (UASTNode): Target FunctionNode or TypeDefinitionNode to summarize.
        file_path (str | Path): File path of the source code.
        signature (str): Extracted function or class signature.
        client (LocalSLMInference | None, optional): Optional LocalSLMInference instance. Loads default if None.
        model (str, optional): Ignored for local SLM, retained for signature compatibility. Defaults to "phi-4-mini".

    Returns:
        str: English semantic summary formatted for Vector Search indexing.
    """
    slm_client = client if client is not None else get_local_slm_client()
    return slm_client.get_summary(
        root_node=root_node,
        target_node=target_node,
        file_path=file_path,
        signature=signature,
    )


# Backward compatibility aliases
summarize_code_node = get_summary
get_llm_model = get_local_slm_client
get_local_summary = get_summary
Phi4MiniInference = LocalSLMInference
LocalSLMClient = LocalSLMInference


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("Initializing Local SLM Phi-4-mini...")
    slm_instance = get_local_slm_client()
    print(
        f"Phi-4-mini initialized successfully from: {slm_instance.resolved_model_path}"
    )
    print("Type 'exit' or 'quit' to exit.")
    print("-" * 50)

    conversation: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "You are a concise, helpful programming assistant.",
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

        conversation.append({"role": "user", "content": user_input})
        print("\nPhi-4-mini: ", end="", flush=True)

        assistant_reply = ""
        for token in slm_instance.stream_chat(conversation):
            assistant_reply += token
            print(token, end="", flush=True)
        print()

        conversation.append({"role": "assistant", "content": assistant_reply})
        if len(conversation) > 20:
            conversation = [conversation[0]] + conversation[-19:]
