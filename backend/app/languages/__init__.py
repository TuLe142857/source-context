from functools import lru_cache

from app.parser import LanguageConfig, LanguageRegistry

from . import java as JAVA
from . import javascript as JAVASCRIPT
from . import python as PYTHON


@lru_cache
def get_language_config() -> list[LanguageConfig]:
    return [PYTHON.get_language_config()]


@lru_cache
def get_language_registry() -> LanguageRegistry:
    return LanguageRegistry(get_language_config())


__all__ = [
    "PYTHON",
    "JAVA",
    "JAVASCRIPT",
    "get_language_config",
    "get_language_registry",
]
