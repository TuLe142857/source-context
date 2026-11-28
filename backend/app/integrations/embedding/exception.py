class EmbeddingError(Exception):
    """An embedding provider call failed (network, auth, rate limit, bad response)."""