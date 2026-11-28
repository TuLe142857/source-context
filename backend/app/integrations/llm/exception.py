class LLMError(Exception):
    """An LLM provider call failed (network, auth, rate limit, bad response)."""
