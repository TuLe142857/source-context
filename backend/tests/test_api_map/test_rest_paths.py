"""Pure REST helpers: URL templates, match keys, router graphs, segment matching."""

import pytest

from app.engine.api_map.handlers.rest_api_handler import (
    compose_route_paths,
    join_url,
    normalize_path,
    segments,
    segments_match,
    split_url,
    suffix_match,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/users/{user_id}", ("/api/v1/users/{}", ["user_id"])),
        ("/api/v1/users/:id/", ("/api/v1/users/{}", ["id"])),
        ("/files/{p:path}", ("/files/{*}", ["p"])),
        ("/u/<int:uid>/x", ("/u/{}/x", ["uid"])),
        ("/f/<path:rest>", ("/f/{*}", ["rest"])),
        ("/blog/[...slug]", ("/blog/{*}", ["slug"])),
        ("/p/[id]", ("/p/{}", ["id"])),
        ("/static/*", ("/static/{*}", [])),
        ("/a//b/", ("/a/b", [])),
        ("/api/v1/Users", ("/api/v1/Users", [])),
        ("", ("/", [])),
        (None, (None, [])),
    ],
)
def test_normalize_path(
    path: str | None, expected: tuple[str | None, list[str]]
) -> None:
    assert normalize_path(path) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "http://catalog:8000/api/v1/products/{pid}?x=1",
            ("http://catalog:8000", "/api/v1/products/{pid}"),
        ),
        ("{CATALOG_URL}/api/v1/items", ("{CATALOG_URL}", "/api/v1/items")),
        ("{$CATALOG_URL}/x", ("{$CATALOG_URL}", "/x")),
        ("{BASE}", ("{BASE}", None)),
        ("http://h", ("http://h", "/")),
        ("/users/{id}#frag", (None, "/users/{id}")),
        (None, (None, None)),
    ],
)
def test_split_url(url: str | None, expected: tuple[str | None, str | None]) -> None:
    assert split_url(url) == expected


@pytest.mark.parametrize(
    ("base", "url", "expected"),
    [
        (
            "http://users:8000/api/v1",
            "/users/{user_id}",
            "http://users:8000/api/v1/users/{user_id}",
        ),
        ("http://h/api/", "x", "http://h/api/x"),
        ("http://h/api", "https://other/x", "https://other/x"),
        (None, "/x", "/x"),
        ("http://h", None, "http://h/{}"),
    ],
)
def test_join_url_follows_httpx(
    base: str | None, url: str | None, expected: str
) -> None:
    assert join_url(base, url) == expected


def test_compose_route_paths() -> None:
    prefixes = {
        "app": "",
        "users": "/users",
        "a": "",
        "b": "/pb",
        "c": "/pc",
        "x": "/x",
        "y": "/y",
    }

    assert compose_route_paths("users", prefixes, [("app", "users", "/api/v1")]) == [
        ("/api/v1/users", True)
    ]
    assert compose_route_paths("orphan", {"orphan": "/o"}, []) == [("/o", False)]
    nested = compose_route_paths(
        "c", prefixes, [("a", "b", "/a"), ("b", "c", "/b"), ("a", "c", "/direct")]
    )
    assert sorted(nested) == [("/a/pb/b/pc", True), ("/direct/pc", True)]
    assert compose_route_paths("x", prefixes, [("x", "y", ""), ("y", "x", "")]) == [
        ("/y/x", True)
    ]


@pytest.mark.parametrize(
    ("call", "endpoint", "expected"),
    [
        ("/api/v1/users/42", "/api/v1/users/{}", True),
        ("/api/v1/users/{}", "/api/v1/users/{}", True),
        ("/files/a/b/c", "/files/{*}", True),
        ("/files", "/files/{*}", False),
        ("/u/7.json", "/u/{}.json", True),
        ("/orders", "/products", False),
    ],
)
def test_segments_match(call: str, endpoint: str, expected: bool) -> None:
    assert segments_match(segments(call), segments(endpoint)) is expected


@pytest.mark.parametrize(
    ("call", "endpoint", "expected"),
    [
        ("/users/{}", "/api/v1/users/{}", True),
        ("/api/v1/users/{}", "/users/{}", True),
        ("/{}/{}", "/api/v1/{}/{}", False),
        ("/users", "/api/users", False),
    ],
)
def test_suffix_match(call: str, endpoint: str, expected: bool) -> None:
    assert suffix_match(segments(call), segments(endpoint)) is expected
