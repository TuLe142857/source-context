"""OpenAI API inference module using gpt-4o-mini for code summarization and LLM interaction."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.embedding.utils import extract_source_code
from app.parser.uast.node import UASTNode

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_openai_client(
    api_key: str | None = None,
) -> OpenAI | None:
    """Loads and caches the OpenAI client instance.

    Args:
        api_key (str | None): Custom OpenAI API Key.

    Returns:
        OpenAI | None: Initialized OpenAI client instance or None if API key is not set.
    """
    key = api_key or settings.OPENAI_API_KEY.get_secret_value()

    if not key or key.strip() == "":
        return None

    return OpenAI(api_key=key)


def get_summary(
    root_node: UASTNode,
    target_node: UASTNode,
    file_path: str | Path,
    signature: str,
    client: OpenAI | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Generates a high-precision, non-generic LLM semantic summary for a code construct using OpenAI gpt-4o-mini API.

    Args:
        root_node (UASTNode): Root UAST container node of the file.
        target_node (UASTNode): Target FunctionNode or TypeDefinitionNode to summarize.
        file_path (str | Path): File path of the source code.
        signature (str): Extracted function or class signature.
        client (OpenAI | None, optional): Optional OpenAI client instance. Loads default client if None.
        model (str, optional): OpenAI model name (defaults to 'gpt-4o-mini').

    Returns:
        str: English semantic summary formatted for Vector Search indexing.
    """
    node_kind = getattr(target_node, "kind", target_node.node_type)
    node_name = target_node.name or "Unnamed"

    openai_client = client if client is not None else get_openai_client()
    target_model = model or settings.OPENAI_MODEL or "gpt-4o-mini"

    if openai_client is None:
        raise RuntimeError(
            "OpenAI API client is not initialized. Please ensure OPENAI_API_KEY is set in environment or config."
        )

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

    response = openai_client.chat.completions.create(
        model=target_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


# Backward compatibility alias
summarize_code_node = get_summary
get_llm_model = get_openai_client


if __name__ == "__main__":
    openai_client = get_openai_client()
    if openai_client is None:
        print("Notice: OPENAI_API_KEY is not set in environment.")
    else:
        print(f"OpenAI Client initialized (model: {settings.OPENAI_MODEL}).")
        print("Type 'exit' or 'quit' to exit.")
        print("-" * 50)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "You are a helpful, smart AI assistant. Answer concisely and accurately in English.",
            }
        ]

        while True:
            user_input = input("\nUser: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            messages.append({"role": "user", "content": user_input})
            print("\nAI: ", end="", flush=True)

            try:
                stream = openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL or "gpt-4o-mini",
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=512,
                    temperature=0.7,
                    stream=True,
                )

                assistant_response = ""
                for chunk in stream:
                    try:
                        content = getattr(chunk, "choices", [None])[0]
                        if (
                            content
                            and hasattr(content, "delta")
                            and getattr(content.delta, "content", None)
                        ):
                            text = content.delta.content
                            assistant_response += text
                            print(text, end="", flush=True)
                    except (KeyError, TypeError, AttributeError):
                        pass

                print()
                messages.append({"role": "assistant", "content": assistant_response})
                if len(messages) > 20:
                    messages = [messages[0]] + messages[-19:]
            except OpenAIError as err:
                print(f"\nOpenAI Error: {err}")
                break
