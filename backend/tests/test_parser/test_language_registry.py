"""Tests for the active parser language registry."""

import pytest
from tree_sitter import Language, Parser

from app.parser import (
    LanguageRegistry,
    UnsupportedLanguageError,
)
from app.parser.languages import get_language_registry
from app.parser.uast import UASTConverter


@pytest.fixture(scope="module")
def registry() -> LanguageRegistry:
    """Return the shared active language registry."""

    return get_language_registry()


def test_load_registry(
    registry: LanguageRegistry,
) -> None:
    """The active registry should load successfully."""

    assert isinstance(registry, LanguageRegistry)


def test_registry_contains_expected_parser_configs(
    registry: LanguageRegistry,
) -> None:
    """Only active Python, JavaScript and TypeScript dialects are registered."""

    assert tuple(registry.supported_languages) == (
        "python",
        "javascript",
        "typescript",
        "tsx",
    )


@pytest.mark.parametrize(
    ("file_name", "expected_config_name"),
    [
        ("service.py", "python"),
        ("types.pyi", "python"),
        ("index.js", "javascript"),
        ("component.jsx", "javascript"),
        ("module.mjs", "javascript"),
        ("config.cjs", "javascript"),
        ("service.ts", "typescript"),
        ("module.mts", "typescript"),
        ("config.cts", "typescript"),
        ("component.tsx", "tsx"),
    ],
)
def test_resolve_parser_config_from_file_name(
    registry: LanguageRegistry,
    file_name: str,
    expected_config_name: str,
) -> None:
    """Each supported extension should resolve to the correct parser."""

    assert registry.resolve_language_name(file_name) == expected_config_name


@pytest.mark.parametrize(
    "parser_config_name",
    [
        "python",
        "javascript",
        "typescript",
        "tsx",
    ],
)
def test_get_language_object(
    registry: LanguageRegistry,
    parser_config_name: str,
) -> None:
    """Every active parser config should expose a Tree-sitter language."""

    language = registry.get_language(
        parser_config_name,
    )

    assert isinstance(language, Language)


@pytest.mark.parametrize(
    "file_name",
    [
        "service.py",
        "types.pyi",
        "index.js",
        "component.jsx",
        "service.ts",
        "component.tsx",
    ],
)
def test_get_parser_for_file(
    registry: LanguageRegistry,
    file_name: str,
) -> None:
    """Every supported file should resolve to a parser."""

    parser = registry.get_parser_for_file(
        file_name,
    )

    assert isinstance(parser, Parser)


@pytest.mark.parametrize(
    "file_name",
    [
        "service.py",
        "index.js",
        "component.jsx",
        "service.ts",
        "component.tsx",
    ],
)
def test_get_converter_for_file(
    registry: LanguageRegistry,
    file_name: str,
) -> None:
    """Every supported file should resolve to a UAST converter."""

    converter = registry.get_converter_for_file(
        file_name,
    )

    assert isinstance(converter, UASTConverter)


@pytest.mark.parametrize(
    ("file_name", "source"),
    [
        (
            "service.py",
            b"def execute(value: int) -> int:\n    return value + 1\n",
        ),
        (
            "index.js",
            b"function execute(value) {\n  return value + 1;\n}\n",
        ),
        (
            "component.jsx",
            b"const App = () => <div>Hello</div>;\n",
        ),
        (
            "service.ts",
            b"interface User { name: string }\nconst user: User = { name: 'Tai' };\n",
        ),
        (
            "component.tsx",
            b"type Props = { title: string };\n"
            b"const App = ({ title }: Props) => "
            b"<h1>{title}</h1>;\n",
        ),
    ],
)
def test_parser_accepts_supported_source(
    registry: LanguageRegistry,
    file_name: str,
    source: bytes,
) -> None:
    """Each active grammar should parse representative valid source."""

    parser = registry.get_parser_for_file(
        file_name,
    )

    tree = parser.parse(source)

    assert tree.root_node.has_error is False


def test_typescript_and_tsx_use_different_languages(
    registry: LanguageRegistry,
) -> None:
    """Plain TypeScript and TSX must use different grammar objects."""

    typescript_language = registry.get_language(
        "typescript",
    )
    tsx_language = registry.get_language(
        "tsx",
    )

    assert typescript_language is not tsx_language


@pytest.mark.parametrize(
    "unsupported_value",
    [
        "java",
        "go",
        "rust",
        "c_sharp",
    ],
)
def test_inactive_language_is_rejected(
    registry: LanguageRegistry,
    unsupported_value: str,
) -> None:
    """Inactive parser configurations should not be accessible."""

    with pytest.raises(UnsupportedLanguageError):
        registry.get_parser(
            unsupported_value,
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "Service.java",
        "main.go",
        "README.md",
        "Dockerfile",
    ],
)
def test_unsupported_file_is_rejected(
    registry: LanguageRegistry,
    file_name: str,
) -> None:
    """Files outside the MVP parser scope should be rejected."""

    with pytest.raises(UnsupportedLanguageError):
        registry.get_parser_for_file(
            file_name,
        )
