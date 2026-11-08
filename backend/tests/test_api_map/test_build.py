"""detect_apis: both approaches merged, framework results first."""

from collections.abc import Callable
from pathlib import Path

from app.engine.api_map.handlers.api_handler import api_metadata
from app.engine.api_map import ApiMapContext, detect_apis
from app.engine.api_map.build import merge_detections, summarize
from app.engine.api_map.languages.python.rest_api import PythonRestApiHandler
from app.engine.graph.model import RestCallNodeModel, RestEndpointNodeModel

type MakeContext = Callable[
    ..., ApiMapContext
]  # the `make_ctx` fixture, see conftest.py


def test_framework_detections_win_on_the_same_anchor(ctx: ApiMapContext) -> None:
    detections = detect_apis(ctx)
    endpoints = [n for n, _ in detections if isinstance(n, RestEndpointNodeModel)]

    # Hướng 1 found the same 8 handlers, with shorter paths: all dropped
    assert len(endpoints) == 8
    assert {api_metadata(n)["detector"] for n in endpoints} == {"framework"}
    assert "GET /api/v1/users/{user_id}" in {n.signature for n in endpoints}


def test_pattern_calls_survive_where_frameworks_saw_nothing(ctx: ApiMapContext) -> None:
    calls = {
        (n.signature, api_metadata(n)["detector"])
        for n, _ in detect_apis(ctx)
        if isinstance(n, RestCallNodeModel)
    }

    assert ("GET /orders", "pattern") in calls  # wrapper client
    assert ("GET /health", "pattern") in calls  # TestClient
    assert sum(detector == "framework" for _, detector in calls) == 7


def test_calls_in_tests_are_flagged(ctx: ApiMapContext) -> None:
    flagged = {n.signature for n, _ in detect_apis(ctx) if api_metadata(n)["in_test"]}

    assert flagged == {"GET /health"}


def test_uids_are_deterministic(make_ctx: MakeContext) -> None:
    first = sorted(n.uid for n, _ in detect_apis(make_ctx("index.scip")))
    second = sorted(n.uid for n, _ in detect_apis(make_ctx("index.scip")))

    assert first == second and len(set(first)) == len(first)


def test_merge_keeps_the_most_confident_duplicate() -> None:
    handler = PythonRestApiHandler()
    ctx = ApiMapContext(1, Path("."), {})

    def node(confidence: float, detector: str = "framework") -> RestEndpointNodeModel:
        return handler.endpoint_node(
            ctx,
            method="GET",
            path="/x",
            framework=None,
            raw=None,
            file="a.py",
            handler_name="h",
            detector=detector,
            rule="r",
            confidence=confidence,
        )

    anchor = ("a.py", 0, 10)
    merged = merge_detections(
        [(node(0.5), anchor), (node(0.9), anchor), (node(0.6, "pattern"), None)]
    )

    assert [api_metadata(n)["confidence"] for n, _ in merged] == [0.9]
    assert summarize(merged) == {"anchored": 1, "endpoint.framework": 1}
