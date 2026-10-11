"""Base interface and common utilities for code inference models."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.embedding.utils import extract_source_code
from app.parser.uast.node import UASTNode


def build_summary_prompts(
    root_node: UASTNode,
    target_node: UASTNode,
    file_path: str | Path,
    signature: str,
) -> tuple[str, str]:
    """Builds standardized system and user prompts for code summarization.

    Args:
        root_node (UASTNode): Root UAST container node of the file.
        target_node (UASTNode): Target node to summarize.
        file_path (str | Path): Source code file path.
        signature (str): Extracted function or class signature.

    Returns:
        tuple[str, str]: Tuple of (system_prompt, user_prompt).
    """
    node_kind = getattr(target_node, "kind", target_node.node_type)
    node_name = target_node.name or "Unnamed"

    source_code = extract_source_code(root_node, target_node, file_path)
    docstring = getattr(target_node, "docstring", None)
    doc_info = f"\n- Docstring: {docstring}" if docstring else ""

    system_prompt = (
        "You are a code intelligence expert. "
        "Analyze the provided code construct and produce a concise, specific 2-3 sentence summary of its exact behavior and operations. "
        "Do NOT use generic filler words, template headings, meta-labels, or bullet points."
        "Clearly describe the purpose and functionality of each function. Avoid generic summaries such as 'Implement {function_name}' under all circumstances."
    )

    user_prompt = f"""Summarize the following code construct in 2-3 direct sentences:

Construct Name: {node_name} ({node_kind})
Signature: {signature}
{doc_info}

Source Code:
```
{source_code}
```

STRICT REQUIREMENTS:
1. Explain what this construct specifically does, its key inputs/outputs, and core operations (e.g. database query, authorization check, data transformation).
2. DO NOT use generic phrases like 'implements business logic', 'processes input parameters', 'executes operations', or 'manages response data'.
3. DO NOT include section titles or labels (e.g., 'Core Purpose:', 'Workflow:', '1.', '2.').
4. Output ONLY the plain summary text.
"""
    return system_prompt, user_prompt


class BaseInference(ABC):
    """Abstract base class defining the unified interface for code inference models."""

    @abstractmethod
    def get_summary(
        self,
        root_node: UASTNode,
        target_node: UASTNode,
        file_path: str | Path,
        signature: str,
        max_tokens: int = 600,
        temperature: float = 0.3,
    ) -> str:
        """Generates a semantic summary for a code construct.

        Args:
            root_node (UASTNode): Root UAST container node.
            target_node (UASTNode): Target construct node to summarize.
            file_path (str | Path): Path to source file.
            signature (str): Extracted signature.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 600.
            temperature (float, optional): Sampling temperature. Defaults to 0.3.

        Returns:
            str: Semantic summary text.
        """
        raise NotImplementedError

    def summarize_code_node(
        self,
        root_node: UASTNode,
        target_node: UASTNode,
        file_path: str | Path,
        signature: str,
        max_tokens: int = 600,
        temperature: float = 0.3,
    ) -> str:
        """Backward-compatible alias for get_summary.

        Args:
            root_node (UASTNode): Root UAST container node.
            target_node (UASTNode): Target construct node to summarize.
            file_path (str | Path): Path to source file.
            signature (str): Extracted signature.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 600.
            temperature (float, optional): Sampling temperature. Defaults to 0.3.

        Returns:
            str: Semantic summary text.
        """
        return self.get_summary(
            root_node=root_node,
            target_node=target_node,
            file_path=file_path,
            signature=signature,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Executes a chat completion call and returns text response.

        Args:
            messages (list[dict[str, Any]]): List of chat messages.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 512.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.

        Returns:
            str: Assistant text response.
        """
        raise NotImplementedError

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Iterator[str]:
        """Streams assistant response chunks for a list of messages.

        Args:
            messages (list[dict[str, Any]]): List of chat messages.
            max_tokens (int, optional): Maximum tokens to generate. Defaults to 512.
            temperature (float, optional): Sampling temperature. Defaults to 0.7.

        Yields:
            str: Generated delta token strings.
        """
        raise NotImplementedError
