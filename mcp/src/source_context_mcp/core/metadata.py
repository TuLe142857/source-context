import importlib.metadata
from functools import lru_cache

_PACKAGE_NAME = "source-context-mcp"


@lru_cache
def get_package_version() -> str:
    """
    Get package version.
    Read from ``pyproject.toml`` file.

    Returns:
        This package version.
    """
    return importlib.metadata.version("source-context-mcp")
