"""REST call -> endpoint matching (RESOLVES_TO rules) and target selection."""

from pathlib import Path

import pytest

from app.engine.api_map import ApiMapContext
from app.engine.api_map.handlers.api_handler import MAX_TARGETS
from app.engine.api_map.languages.python.rest_api import PythonRestApiHandler
from app.engine.graph.model import RestCallNodeModel, RestEndpointNodeModel

HANDLER = PythonRestApiHandler()


def endpoint(
    path: str, method: str = "GET", project_id: int = 1, confidence: float = 1.0
) -> RestEndpointNodeModel:
    return HANDLER.endpoint_node(
        ApiMapContext(project_id, Path("."), {}),
        method=method,
        path=path,
        framework="fastapi",
        raw=None,
        file=f"server_{path}.py",
        handler_name=f"h{path}",
        detector="framework",
        rule="test",
        confidence=confidence,
    )


def call(
    url: str | None,
    method: str | None = "GET",
    project_id: int = 2,
    confidence: float = 1.0,
) -> RestCallNodeModel:
    return HANDLER.call_node(
        ApiMapContext(project_id, Path("."), {}),
        method=method,
        url=url,
        library="requests",
        raw=None,
        file="client.py",
        scope=f"f{url}",
        detector="framework",
        rule="test",
        confidence=confidence,
    )


@pytest.mark.parametrize(
    ("call_url", "endpoint_path", "rule"),
    [
        (
            "http://users:8000/api/v1/users/{user_id}",
            "/api/v1/users/{user_id}",
            "exact",
        ),
        ("http://users:8000/api/v1/users/1", "/api/v1/users/{user_id}", "pattern"),
        ("/users/{id}", "/api/v1/users/{user_id}", "suffix"),
        ("http://h/api/v1/users/1/orders", "/api/v1/users/{user_id}", None),
    ],
)
def test_match_rules(call_url: str, endpoint_path: str, rule: str | None) -> None:
    matched = HANDLER.match_api(endpoint(endpoint_path), call(call_url))

    assert (matched[0] if matched else None) == rule


def test_method_must_agree_unless_unknown_or_any() -> None:
    assert (
        HANDLER.match_api(endpoint("/users/{id}", "DELETE"), call("/users/1", "GET"))
        is None
    )
    assert (
        HANDLER.match_api(endpoint("/users/{id}", "*"), call("/users/1", "GET"))
        is not None
    )

    known = HANDLER.match_api(endpoint("/users/{id}"), call("/users/1", "GET"))
    unknown = HANDLER.match_api(endpoint("/users/{id}"), call("/users/1", None))
    assert known is not None and unknown is not None
    assert unknown[1] < known[1]


def test_confidence_combines_rule_and_detections() -> None:
    matched = HANDLER.match_api(
        endpoint("/a/{id}", confidence=0.9), call("/a/1", confidence=0.5)
    )

    assert matched == ("pattern", round(0.85 * 0.9 * 0.5, 3))


def test_placeholder_only_path_is_unknown() -> None:
    node = call("{}{}")

    assert node.path is None and node.match_key is None and node.is_dynamic
    assert HANDLER.match_api(endpoint("/health"), node) is None


def test_resolve_call_keeps_best_tier() -> None:
    endpoints = [
        endpoint("/api/v1/users/{id}"),
        endpoint("/users/{id}"),
        endpoint("/api/v1/orders"),
    ]

    matches = HANDLER.resolve_call(call("http://users:8000/api/v1/users/7"), endpoints)

    assert [(e.path, rule) for e, rule, _ in matches] == [
        ("/api/v1/users/{id}", "pattern")
    ]


def test_resolve_call_prefers_own_project_without_host() -> None:
    own, other = endpoint("/health", project_id=2), endpoint("/health", project_id=3)

    local = HANDLER.resolve_call(call("/health", project_id=2), [own, other])
    remote = HANDLER.resolve_call(
        call("http://catalog:8000/health", project_id=2), [own, other]
    )

    assert [e.project_id for e, _, _ in local] == [2]
    assert sorted(e.project_id for e, _, _ in remote) == [2, 3]


def test_resolve_call_gives_up_when_too_ambiguous() -> None:
    endpoints = [endpoint("/health", project_id=10 + i) for i in range(MAX_TARGETS + 1)]

    assert HANDLER.resolve_call(call("http://somewhere/health"), endpoints) == []
