"""Protocol handler interface shared by every API kind and language."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

from app.engine.graph.model import ApiCallNodeModel, ApiEndpointNodeModel, ApiNodeModel

if TYPE_CHECKING:
    from app.engine.api_map.context import ApiMapContext

API_KIND = Literal["rest", "sse", "websocket", "grpc", "graphql"]

type Anchor = tuple[str, int, int]
"""``(file path, start_byte, end_byte)`` of the UAST node an API hangs on: the handler
``Function`` of an endpoint, the ``Call`` of a call. Spans equal the tree-sitter node spans."""

type Detection = tuple[ApiNodeModel, Anchor | None]
"""An unsaved API node and where it sits in the code."""

type Match = tuple[ApiEndpointNodeModel, str, float]
"""An endpoint a call reaches, with the ``rule`` and ``confidence`` of ``RESOLVES_TO``."""

MAX_TARGETS = 3
"""A call reaching more endpoints than this at the same confidence is too ambiguous to link."""

TIE_MARGIN = 0.05
"""Matches within this distance of the best confidence count as equally good."""


def api_uid(*parts: object) -> str:
    """Deterministic uid: re-running the extraction yields the same uid for the same API."""

    return hashlib.sha1("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()


def is_test_path(path: str) -> bool:
    """Whether a file belongs to the test suite: calls there hit the app under test, not a service."""

    file = PurePosixPath(path)
    return (
        bool({"test", "tests"} & set(file.parts[:-1]))
        or file.name.startswith("test_")
        or file.stem.endswith("_test")
    )


def api_metadata(node: ApiNodeModel) -> dict[str, Any]:
    """``metadata`` of an API node: ``detector``, ``rule``, ``confidence``... (never ``None``)."""

    return node.metadata or {}


def detection_confidence(node: ApiNodeModel) -> float:
    """Confidence the detector gave this node, kept in ``metadata``."""

    value = api_metadata(node).get("confidence", 0.5)
    return float(value) if isinstance(value, int | float) else 0.5


class ApiHandler(ABC):
    """One protocol (``kind``) in one language.

    Detection is per language (``detect_api``), matching per protocol (``match_api``): every
    language handler of a kind inherits the same matching from its protocol class.
    """

    def __init__(
        self, kind: API_KIND, language: str, languages: tuple[str, ...] = ()
    ) -> None:
        """
        Args:
            kind: Protocol of the APIs this handler finds.
            language: Main language name.
            languages: Every language the handler reads, when one detector serves a family
                (``javascript``, ``typescript``, ``tsx``): an Express app in TypeScript mounts
                routers written in JavaScript. Defaults to ``(language,)``.
        """

        self._kind: API_KIND = kind
        self._language = language
        self._languages = languages or (language,)

    @property
    def kind(self) -> API_KIND:
        return self._kind

    @property
    def language(self) -> str:
        return self._language

    @property
    def languages(self) -> tuple[str, ...]:
        return self._languages

    @abstractmethod
    def detect_api(self, ctx: ApiMapContext) -> list[Detection]:
        """Every endpoint and call of this protocol in the project's ``self.language`` files."""

    @abstractmethod
    def match_api(
        self, endpoint: ApiEndpointNodeModel, call: ApiCallNodeModel
    ) -> tuple[str, float] | None:
        """``(rule, confidence)`` - the properties of ``RESOLVES_TO``, confidence in [0, 1] -
        or ``None`` when the call cannot reach the endpoint."""

    def resolve_call(
        self, call: ApiCallNodeModel, endpoints: list[ApiEndpointNodeModel]
    ) -> list[Match]:
        """Endpoints a call reaches: the best confidence tier, at most ``MAX_TARGETS``.

        Brute force over every endpoint; protocols with many endpoints override it with an index.
        """

        return best_matches(
            [
                (endpoint, *matched)
                for endpoint in endpoints
                if (matched := self.match_api(endpoint, call))
            ]
        )


def best_matches(scored: list[Match]) -> list[Match]:
    """Keep the matches tied with the best one; drop everything when too many are tied."""

    if not scored:
        return []
    best = max(confidence for _, _, confidence in scored)
    top = [match for match in scored if match[2] >= best - TIE_MARGIN]
    return top if len(top) <= MAX_TARGETS else []
