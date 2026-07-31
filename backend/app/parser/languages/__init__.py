"""Active language configurations for the source parser."""

from functools import lru_cache

from app.parser.language_registry import LanguageRegistry

from . import javascript
from . import python
from . import typescript


@lru_cache
def get_language_registry() -> LanguageRegistry:
    """Return the active parser registry.

    Public source-language support:
    - Python
    - JavaScript
    - TypeScript

    TypeScript and TSX use separate internal parser configurations.
    """

    return LanguageRegistry(
        [
            python.get_language_config(),
            javascript.get_language_config(),
            typescript.get_typescript_language_config(),
            typescript.get_tsx_language_config(),
        ],
    )
