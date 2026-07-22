from functools import lru_cache

from app.parser.language_registry import LanguageConfig
from app.parser.uast import BaseUASTConverter, UASTConverter

from .adapter import get_adapter, get_language


@lru_cache()
def get_converter() -> UASTConverter:
    return BaseUASTConverter(get_adapter())


@lru_cache()
def get_language_config() -> LanguageConfig:
    return LanguageConfig(
        name="python",
        language_factory=get_language,
        converter_factory=get_converter,
        extensions=[".py"],
    )


__all__ = ["get_language_config"]
