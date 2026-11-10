"""REST protocol: URL templates, match keys, node building and call -> endpoint matching.

Everything here is language independent; detection lives in ``languages/<language>/``.
"""

from __future__ import annotations

import re
from abc import ABC
from collections import defaultdict
from typing import TYPE_CHECKING

from app.engine.graph.model import (
    ApiCallNodeModel,
    ApiEndpointNodeModel,
    RestCallNodeModel,
    RestEndpointNodeModel,
)

from .api_handler import (
    API_KIND,
    TIE_MARGIN,
    ApiHandler,
    Match,
    api_uid,
    best_matches,
    detection_confidence,
    is_test_path,
)

if TYPE_CHECKING:
    from app.engine.api_map.context import ApiMapContext

type Mount = tuple[str, str, str]
"""``(parent key, child key, prefix)``: FastAPI include_router/mount, Flask register_blueprint,
Express app.use... A router graph is the same thing in every framework."""

RULE_SCORE = {"exact": 1.0, "pattern": 0.85, "suffix": 0.6}
UNKNOWN_METHOD_FACTOR = 0.8
LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0")

_SCHEME_HOST = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^/?#]*")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_MULTI = re.compile(r"\{[^{}/]*:path\}|<path:[^>]+>|\[\[?\.\.\.[^\]]+\]\]?|(?<=/)\*\w*")
_ONE = re.compile(
    r"\$\{[^}]*\}|\{[^{}/]*\}|<[^<>/]+>|(?<=/):[A-Za-z_]\w*\??|\[[^\]/]+\]"
)
_NAME = re.compile(
    r"\{\$?([A-Za-z_]\w*)[^{}]*\}|<(?:[^:<>]+:)?([A-Za-z_]\w*)>|(?<=/):([A-Za-z_]\w*)"
    r"|\[(?:\.\.\.)?([A-Za-z_]\w*)\]"
)


# ---------------------------------------------------------------------- URL templates


def split_url(url: str | None) -> tuple[str | None, str | None]:
    """``(target_hint, path)`` of a URL template.

    target_hint: scheme+host (``http://users:8000``) or the leading base placeholder (``{CATALOG_URL}``).
    path: the rest without query and fragment; ``None`` when unknown (``{BASE}`` alone).
    """

    if url is None:
        return None, None
    rest, hint = url.strip(), None
    if match := _SCHEME_HOST.match(rest):
        hint, rest = match.group(0), rest[match.end() :]
    elif rest.startswith("{") and (end := rest.find("}")) > 0:
        hint, rest = rest[: end + 1], rest[end + 1 :]
    rest = re.split(r"[?#]", rest, maxsplit=1)[0]
    if not rest:
        return hint, "/" if hint is not None and _SCHEME_HOST.match(hint) else None
    return hint, rest if rest.startswith("/") else "/" + rest


def join_url(base: str | None, url: str | None) -> str | None:
    """httpx semantics: a relative URL is appended to the base path, an absolute one replaces it."""

    if base is None:
        return url
    if url is None:
        return base.rstrip("/") + "/{}"
    if _SCHEME_HOST.match(url):
        return url
    return base.rstrip("/") + "/" + url.lstrip("/") if url else base


def normalize_path(path: str | None) -> tuple[str | None, list[str]]:
    """``(match_key, parameter names)``: ``/api/v1/users/:id/`` -> ``("/api/v1/users/{}", ["id"])``.

    Parameters of every framework syntax become ``{}`` (one segment) or ``{*}`` (several
    segments); duplicate and trailing slashes go; case is kept.
    """

    if path is None:
        return None, []
    names = [next(group for group in groups if group) for groups in _NAME.findall(path)]
    key = _ONE.sub("{}", _MULTI.sub("\x00", path)).replace("\x00", "{*}")
    return "/" + "/".join(segment for segment in key.split("/") if segment), names


def compose_route_paths(
    router: str, prefixes: dict[str, str], mounts: list[Mount]
) -> list[tuple[str, bool]]:
    """Every full prefix of ``router``, one per chain of mounts reaching it from a root.

    Returns ``(prefix, mounted)``; a router no mount reaches yields its own prefix with
    ``mounted=False``. Cycles are cut by tracking the routers on the current chain.
    """

    def chains(key: str, on_chain: frozenset[str]) -> list[str]:
        own = prefixes.get(key, "")
        parents = [
            (parent, prefix)
            for parent, child, prefix in mounts
            if child == key and parent not in on_chain
        ]
        if not parents:
            return [own]
        return [
            chain + prefix + own
            for parent, prefix in parents
            for chain in chains(parent, on_chain | {key})
        ]

    mounted = any(child == router for _, child, _ in mounts)
    return [(prefix, mounted) for prefix in dict.fromkeys(chains(router, frozenset()))]


# ---------------------------------------------------------------------- segment matching


def segments(match_key: str) -> list[str]:
    return [segment for segment in match_key.split("/") if segment]


def segment_match(a: str, b: str) -> bool:
    """Two segments are compatible: equal, one is a parameter, or a partial one (``{}.json``) matches."""

    if a == b or "{}" in (a, b) or "{*}" in (a, b):
        return True
    if "{}" in a or "{}" in b:
        pattern, value = (a, b) if "{}" in a else (b, a)
        return (
            re.fullmatch(re.escape(pattern).replace(r"\{\}", "[^/]+"), value)
            is not None
        )
    return False


def segments_match(call: list[str], endpoint: list[str]) -> bool:
    """Segment-wise compatibility; an endpoint ``{*}`` swallows the rest (at least one segment)."""

    for index, segment in enumerate(endpoint):
        if segment == "{*}":
            return len(call) > index
        if index >= len(call) or not segment_match(call[index], segment):
            return False
    return len(call) == len(endpoint)


def suffix_match(call: list[str], endpoint: list[str]) -> bool:
    """The shorter side (>= 2 segments, >= 1 literal) matches the tail of the longer one."""

    shorter, longer = (
        (call, endpoint) if len(call) < len(endpoint) else (endpoint, call)
    )
    if (
        len(shorter) < 2
        or len(shorter) == len(longer)
        or all("{" in s for s in shorter)
    ):
        return False
    return all(
        segment_match(a, b)
        for a, b in zip(shorter, longer[-len(shorter) :], strict=True)
    )


def _is_local_target(target_hint: str | None) -> bool:
    """No host, a base-URL placeholder or a loopback host: probably the caller's own service."""

    if target_hint is None or target_hint.startswith("{"):
        return True
    return any(host in target_hint for host in LOCAL_HOSTS)


# ---------------------------------------------------------------------- handler


class RestApiHandler(ApiHandler, ABC):
    """REST protocol: node building, match keys and matching. Detection stays per language."""

    def __init__(
        self, kind: API_KIND, language: str, languages: tuple[str, ...] = ()
    ) -> None:
        super().__init__(kind, language, languages)
        self._index_cache: (
            tuple[list[ApiEndpointNodeModel], dict[int, list[ApiEndpointNodeModel]]]
            | None
        ) = None
        """Endpoint index of the last list ``resolve_call`` saw: linking passes the same list
        for every call of a protocol."""

    def endpoint_node(
        self,
        ctx: ApiMapContext,
        *,
        method: str,
        path: str,
        framework: str | None,
        raw: str | None,
        file: str,
        handler_name: str | None,
        detector: str,
        rule: str,
        confidence: float,
        **extra: object,
    ) -> RestEndpointNodeModel:
        """Unsaved endpoint node with its uid, match key and metadata computed."""

        match_key, params = normalize_path(path)
        return RestEndpointNodeModel(
            uid=api_uid(
                ctx.project_id,
                self.kind,
                "endpoint",
                method,
                match_key,
                file,
                handler_name,
            ),
            project_id=ctx.project_id,
            match_key=match_key,
            signature=f"{method} {path}",
            raw=raw,
            file_node_uid=ctx.file_uids.get(file),
            framework=framework,
            http_method=method,
            path=path,
            path_params=params,
            metadata={
                "detector": detector,
                "rule": rule,
                "confidence": round(confidence, 3),
                "handler": handler_name,
                "in_test": is_test_path(file),
                **extra,
            },
        )

    def call_node(
        self,
        ctx: ApiMapContext,
        *,
        method: str | None,
        url: str | None,
        library: str | None,
        raw: str | None,
        file: str,
        scope: str,
        ordinal: int = 1,
        detector: str,
        rule: str,
        confidence: float,
        **extra: object,
    ) -> RestCallNodeModel:
        """Unsaved call node; byte offsets stay out of the uid, they move with every edit.

        A path made of placeholders only (``/{}`` from ``self.base + path``) is unknown: as a key
        it would match every one-segment endpoint of the workspace.
        """

        target_hint, path = split_url(url)
        if path is not None and not _PLACEHOLDER.sub("", path).strip("/"):
            path = None
        match_key, _ = normalize_path(path)
        return RestCallNodeModel(
            uid=api_uid(
                ctx.project_id, self.kind, "call", file, scope, method, raw, ordinal
            ),
            project_id=ctx.project_id,
            match_key=match_key,
            signature=f"{method or '?'} {path or url or '?'}",
            raw=raw,
            file_node_uid=ctx.file_uids.get(file),
            library=library,
            is_dynamic=path is None or "{" in path,
            target_hint=target_hint,
            http_method=method,
            path=path,
            metadata={
                "detector": detector,
                "rule": rule,
                "confidence": round(confidence, 3),
                "url": url,
                "scope": scope,
                "in_test": is_test_path(file),
                **extra,
            },
        )

    def match_api(
        self, endpoint: ApiEndpointNodeModel, call: ApiCallNodeModel
    ) -> tuple[str, float] | None:
        if not (
            isinstance(endpoint, RestEndpointNodeModel)
            and isinstance(call, RestCallNodeModel)
        ):
            return None
        if call.match_key is None or endpoint.match_key is None:
            return None
        if call.http_method and endpoint.http_method not in (call.http_method, "*"):
            return None

        call_segments, endpoint_segments = (
            segments(call.match_key),
            segments(endpoint.match_key),
        )
        if call.match_key == endpoint.match_key:
            rule = "exact"
        elif segments_match(call_segments, endpoint_segments):
            rule = "pattern"
        elif suffix_match(call_segments, endpoint_segments):
            rule = "suffix"
        else:
            return None

        confidence = (
            RULE_SCORE[rule]
            * detection_confidence(call)
            * detection_confidence(endpoint)
        )
        if call.http_method is None:
            confidence *= UNKNOWN_METHOD_FACTOR
        return rule, round(confidence, 3)

    def resolve_call(
        self, call: ApiCallNodeModel, endpoints: list[ApiEndpointNodeModel]
    ) -> list[Match]:
        """Indexed matching: exact and pattern candidates come from the endpoints with the same
        segment count (or a ``{*}``); the full scan for ``suffix`` only runs when they gave nothing.

        Local floor: a call without a real host prefers endpoints of its own project, so a
        ``/health`` call is not linked to every service of the workspace.
        """

        if call.match_key is None:
            return []
        index = self._index(endpoints)
        length = len(segments(call.match_key))
        candidates = index.get(length, []) + index.get(-1, [])
        scored = [
            (endpoint, *m)
            for endpoint in candidates
            if (m := self.match_api(endpoint, call))
        ]
        if not scored:
            scored = [
                (endpoint, *m)
                for endpoint in endpoints
                if (m := self.match_api(endpoint, call))
            ]

        if isinstance(call, RestCallNodeModel) and _is_local_target(call.target_hint):
            local = [
                match for match in scored if match[0].project_id == call.project_id
            ]
            if local:
                best_local = max(confidence for _, _, confidence in local)
                if (
                    best_local
                    >= max(confidence for _, _, confidence in scored) - TIE_MARGIN
                ):
                    scored = local
        return best_matches(scored)

    def _index(
        self, endpoints: list[ApiEndpointNodeModel]
    ) -> dict[int, list[ApiEndpointNodeModel]]:
        """Endpoints by segment count; ``-1`` holds those ending with ``{*}``. Cached per list."""

        if self._index_cache is not None and self._index_cache[0] is endpoints:
            return self._index_cache[1]
        index: dict[int, list[ApiEndpointNodeModel]] = defaultdict(list)
        for endpoint in endpoints:
            if endpoint.match_key is None:
                continue
            key_segments = segments(endpoint.match_key)
            index[
                -1 if key_segments and key_segments[-1] == "{*}" else len(key_segments)
            ].append(endpoint)
        self._index_cache = (endpoints, index)
        return index
