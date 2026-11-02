from collections import defaultdict
from typing import Sequence, Type
from .base import BaseRouteExtractor


class RouteExtractorRegistry:
    """Registry maintaining available language and framework route extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, list[BaseRouteExtractor]] = defaultdict(list)

    def register(self, extractor: BaseRouteExtractor) -> None:
        lang = extractor.language.lower()
        self._extractors[lang].append(extractor)

    def get_extractors_for_language(self, language: str) -> Sequence[BaseRouteExtractor]:
        return self._extractors.get(language.lower(), [])

    def get_all_extractors(self) -> Sequence[BaseRouteExtractor]:
        res = []
        for extractors in self._extractors.values():
            res.extend(extractors)
        return res


_GLOBAL_REGISTRY = RouteExtractorRegistry()


def register_route_extractor(cls: Type[BaseRouteExtractor]) -> Type[BaseRouteExtractor]:
    """Decorator to register a RouteExtractor implementation."""
    instance = cls()
    _GLOBAL_REGISTRY.register(instance)
    return cls


def get_route_extractor_registry() -> RouteExtractorRegistry:
    return _GLOBAL_REGISTRY
