"""Semantic tests for the Python Tree-sitter to UAST conversion."""

from collections.abc import Iterator
from textwrap import dedent

from app.parser.languages import get_language_registry
from app.parser.uast import (
    CallNode,
    FunctionNode,
    ImportNode,
    TypeDefinitionNode,
    UASTNode,
    VariableNode,
)


def parse_python(
    source: str,
    *,
    file_path: str = "sample.py",
) -> tuple[UASTNode, bytes]:
    """Parse Python source and return the UAST root and source bytes."""

    source_bytes = source.encode("utf-8")
    registry = get_language_registry()

    parser = registry.get_parser_for_file(
        file_path,
    )
    converter = registry.get_converter_for_file(
        file_path,
    )

    tree = parser.parse(source_bytes)

    assert tree.root_node.has_error is False

    root = converter.convert(
        tree,
        source_bytes=source_bytes,
        file_path=file_path,
    )

    return root, source_bytes


def walk_uast(
    node: UASTNode,
) -> Iterator[UASTNode]:
    """Yield a UAST node and all its descendants."""

    yield node

    for child in node.children:
        yield from walk_uast(child)


def find_nodes(
    root: UASTNode,
    node_type: type[UASTNode],
    *,
    name: str | None = None,
) -> list[UASTNode]:
    """Find UAST nodes by runtime type and optional name."""

    return [
        node
        for node in walk_uast(root)
        if isinstance(node, node_type) and (name is None or node.name == name)
    ]


def find_single_node(
    root: UASTNode,
    node_type: type[UASTNode],
    *,
    name: str | None = None,
) -> UASTNode:
    """Find exactly one matching UAST node."""

    matches = find_nodes(
        root,
        node_type,
        name=name,
    )

    assert len(matches) == 1

    return matches[0]


def test_python_root_contains_file_metadata() -> None:
    source = "value = 1\n"

    root, _ = parse_python(
        source,
        file_path="src/service.py",
    )

    assert root.name == "src/service.py"
    assert root.metadata == {}

    root_dict = root.to_dict()

    assert root_dict["path"] == "src/service.py"
    assert root_dict["language"] == "python"


def test_python_function_metadata_and_parameters() -> None:
    source = dedent(
        '''\
        @cache
        async def fetch(
            user_id: int,
            limit=10,
            *args,
            **kwargs,
        ) -> str:
            """Load one user."""
            client.users.get(user_id)
            return str(user_id)
        ''',
    )

    root, source_bytes = parse_python(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="fetch",
    )

    assert isinstance(function, FunctionNode)
    assert function.kind == "function"
    assert function.return_type == "str"
    assert function.is_async is True
    assert function.decorators == ["@cache"]
    assert function.docstring == '"""Load one user."""'

    function_source = source_bytes[function.start_byte : function.end_byte].decode(
        "utf-8"
    )

    # Decorator is a prefix sibling in the CST and is intentionally
    # outside the function_definition byte range.
    assert function_source.startswith(
        "async def fetch",
    )

    parameters = {
        node.name: node
        for node in find_nodes(
            function,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    }

    assert set(parameters) == {
        "user_id",
        "limit",
        "args",
        "kwargs",
    }

    user_id = parameters["user_id"]
    limit = parameters["limit"]

    assert isinstance(user_id, VariableNode)
    assert user_id.data_type == "int"

    assert isinstance(limit, VariableNode)
    assert limit.initial_value == "10"

    for parameter in parameters.values():
        assert parameter.parent_id == function.id


def test_python_calls_have_name_and_subject() -> None:
    source = dedent(
        """\
        def execute(value: int) -> str:
            client.users.get(value)
            return str(value)
        """,
    )

    root, _ = parse_python(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="execute",
    )

    calls = [
        node
        for node in find_nodes(
            function,
            CallNode,
        )
        if isinstance(node, CallNode)
    ]

    call_by_name = {call.name: call for call in calls}

    assert call_by_name["get"].subject == "client.users"
    assert call_by_name["str"].subject is None

    assert call_by_name["get"].parent_id == function.id
    assert call_by_name["str"].parent_id == function.id


def test_python_class_bases_constructor_method_and_field() -> None:
    source = dedent(
        '''\
        class UserService(
            BaseService,
            mixins.LoggingMixin,
            metaclass=ABCMeta,
        ):
            """User operations."""

            VERSION: str = "1"

            def __init__(self, repository):
                self.repository = repository

            def find(self, user_id: int) -> str:
                return self.repository.find(user_id)
        ''',
    )

    root, _ = parse_python(source)

    class_node = find_single_node(
        root,
        TypeDefinitionNode,
        name="UserService",
    )

    assert isinstance(class_node, TypeDefinitionNode)
    assert class_node.kind == "class"
    assert class_node.base_types == [
        "BaseService",
        "mixins.LoggingMixin",
    ]
    assert class_node.docstring == '"""User operations."""'

    constructor = find_single_node(
        class_node,
        FunctionNode,
        name="__init__",
    )
    method = find_single_node(
        class_node,
        FunctionNode,
        name="find",
    )
    version = find_single_node(
        class_node,
        VariableNode,
        name="VERSION",
    )

    assert isinstance(constructor, FunctionNode)
    assert constructor.kind == "constructor"
    assert constructor.parent_id == class_node.id

    assert isinstance(method, FunctionNode)
    assert method.kind == "method"
    assert method.return_type == "str"
    assert method.parent_id == class_node.id

    assert isinstance(version, VariableNode)
    assert version.data_type == "str"
    assert version.initial_value == '"1"'
    assert version.parent_id == class_node.id


def test_python_nested_function_keeps_parent_relationship() -> None:
    source = dedent(
        """\
        def outer():
            def inner():
                return 1

            return inner()
        """,
    )

    root, _ = parse_python(source)

    outer = find_single_node(
        root,
        FunctionNode,
        name="outer",
    )
    inner = find_single_node(
        root,
        FunctionNode,
        name="inner",
    )

    assert inner.parent_id == outer.id


def test_python_import_module_paths() -> None:
    source = dedent(
        """\
        import os
        from app.services import UserService
        """,
    )

    root, _ = parse_python(source)

    imports = [
        node
        for node in find_nodes(
            root,
            ImportNode,
        )
        if isinstance(node, ImportNode)
    ]

    module_paths = {import_node.module_path for import_node in imports}

    assert module_paths == {
        "os",
        "app.services",
    }


def test_augmented_assignment_is_not_a_second_definition() -> None:
    source = dedent(
        """\
        count = 0
        count += 1
        """,
    )

    root, _ = parse_python(source)

    count_variables = find_nodes(
        root,
        VariableNode,
        name="count",
    )

    assert len(count_variables) == 1

    count_variable = count_variables[0]

    assert isinstance(count_variable, VariableNode)
    assert count_variable.initial_value == "0"


def test_python_byte_ranges_support_unicode_and_crlf() -> None:
    source = "def tính_tổng(a: int, b: int) -> int:\r\n    return a + b\r\n"

    root, source_bytes = parse_python(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="tính_tổng",
    )

    function_bytes = source_bytes[function.start_byte : function.end_byte]

    function_text = function_bytes.decode(
        "utf-8",
    )

    assert function_text.startswith(
        "def tính_tổng",
    )
    assert function_text.endswith(
        "return a + b",
    )
