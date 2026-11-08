from functools import lru_cache

# not from the package root: app.engine.api_map/__init__ imports build.py, which imports this
from app.engine.api_map.api_registry import ApiRegistry

from .javascript.rest_api import JavascriptRestApiHandler
from .python.rest_api import PythonRestApiHandler


@lru_cache
def get_api_handler_registry() -> ApiRegistry:
    """Every handler the API map runs: one per (protocol, language)."""

    return ApiRegistry([PythonRestApiHandler(), JavascriptRestApiHandler()])
