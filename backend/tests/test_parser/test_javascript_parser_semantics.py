"""Semantic tests for JavaScript and JSX UAST conversion."""

from collections.abc import Iterator
from textwrap import dedent

from tree_sitter import Query

from app.parser.languages.javascript.adapter import get_query

from app.parser.languages import get_language_registry
from app.parser.uast import (
    CallNode,
    FunctionNode,
    ImportNode,
    TypeDefinitionNode,
    UASTNode,
    VariableNode,
)


def test_javascript_query_compiles() -> None:
    """The UAST query must compile against the installed JS grammar."""

    query = get_query()

    assert isinstance(query, Query)


def parse_javascript(
    source: str,
    *,
    file_path: str = "sample.js",
) -> tuple[UASTNode, bytes]:
    """Parse JavaScript source into UAST."""

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
    """Yield a node and all descendants."""

    yield node

    for child in node.children:
        yield from walk_uast(child)


def find_nodes(
    root: UASTNode,
    node_type: type[UASTNode],
    *,
    name: str | None = None,
) -> list[UASTNode]:
    """Find nodes by runtime type and optional name."""

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
    """Find exactly one matching node."""

    matches = find_nodes(
        root,
        node_type,
        name=name,
    )

    assert len(matches) == 1

    return matches[0]


def test_javascript_root_contains_file_metadata() -> None:
    root, _ = parse_javascript(
        "const value = 1;\n",
        file_path="src/service.js",
    )

    assert root.name == "src/service.js"

    root_dict = root.to_dict()

    assert root_dict["path"] == "src/service.js"
    assert root_dict["language"] == "javascript"


def test_function_declaration_parameters_and_docstring() -> None:
    source = dedent(
        """\
        /**
         * Fetch one user.
         */
        async function fetchUser(id, limit = 10, ...flags) {
          return client.users.get(id);
        }
        """,
    )

    root, _ = parse_javascript(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="fetchUser",
    )

    assert isinstance(function, FunctionNode)
    assert function.kind == "function"
    assert function.is_async is True
    assert function.docstring is not None
    assert "Fetch one user" in function.docstring

    parameters = {
        node.name: node
        for node in find_nodes(
            function,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    }

    assert set(parameters) == {
        "id",
        "limit",
        "flags",
    }

    limit = parameters["limit"]

    assert isinstance(limit, VariableNode)
    assert limit.initial_value == "10"

    for parameter in parameters.values():
        assert parameter.parent_id == function.id


def test_arrow_function_is_not_duplicated_as_constant() -> None:
    source = dedent(
        """\
        const fetchUser = async (id = 1, ...flags) => {
          return api.get(id);
        };
        """,
    )

    root, _ = parse_javascript(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="fetchUser",
    )

    assert isinstance(function, FunctionNode)
    assert function.is_async is True

    duplicate_variables = find_nodes(
        root,
        VariableNode,
        name="fetchUser",
    )

    assert duplicate_variables == []

    parameters = {
        node.name: node
        for node in find_nodes(
            function,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    }

    assert set(parameters) == {
        "id",
        "flags",
    }

    assert parameters["id"].initial_value == "1"


def test_constants_and_variables_have_correct_kind() -> None:
    source = dedent(
        """\
        const version = "1.0";
        let retryCount = 0;
        var legacyMode = true;
        """,
    )

    root, _ = parse_javascript(source)

    version = find_single_node(
        root,
        VariableNode,
        name="version",
    )
    retry_count = find_single_node(
        root,
        VariableNode,
        name="retryCount",
    )
    legacy_mode = find_single_node(
        root,
        VariableNode,
        name="legacyMode",
    )

    assert isinstance(version, VariableNode)
    assert version.kind == "constant"
    assert version.initial_value == '"1.0"'

    assert isinstance(retry_count, VariableNode)
    assert retry_count.kind == "variable"
    assert retry_count.initial_value == "0"

    assert isinstance(legacy_mode, VariableNode)
    assert legacy_mode.kind == "variable"
    assert legacy_mode.initial_value == "true"


def test_class_base_constructor_method_and_field() -> None:
    source = dedent(
        """\
        class UserService extends BaseService {
          version = "1";

          constructor(repository) {
            this.repository = repository;
          }

          static async create(repository) {
            return new UserService(repository);
          }

          find(userId) {
            return this.repository.find(userId);
          }
        }
        """,
    )

    root, _ = parse_javascript(source)

    class_node = find_single_node(
        root,
        TypeDefinitionNode,
        name="UserService",
    )

    assert isinstance(class_node, TypeDefinitionNode)
    assert class_node.base_types == [
        "BaseService",
    ]

    constructor = find_single_node(
        class_node,
        FunctionNode,
        name="constructor",
    )
    create_method = find_single_node(
        class_node,
        FunctionNode,
        name="create",
    )
    find_method = find_single_node(
        class_node,
        FunctionNode,
        name="find",
    )
    version = find_single_node(
        class_node,
        VariableNode,
        name="version",
    )

    assert isinstance(constructor, FunctionNode)
    assert constructor.kind == "constructor"
    assert constructor.parent_id == class_node.id

    assert isinstance(create_method, FunctionNode)
    assert create_method.kind == "method"
    assert create_method.is_static is True
    assert create_method.is_async is True

    assert isinstance(find_method, FunctionNode)
    assert find_method.kind == "method"

    assert isinstance(version, VariableNode)
    assert version.kind == "field"
    assert version.initial_value == '"1"'


def test_calls_have_name_and_subject() -> None:
    source = dedent(
        """\
        function execute(value) {
          client.users.get(value);
          String(value);
          const service = new UserService();
          handlers[type](value);
        }
        """,
    )

    root, _ = parse_javascript(source)

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
    assert call_by_name["String"].subject is None
    assert call_by_name["UserService"].subject is None
    assert call_by_name["type"].subject == "handlers"


def test_es_module_and_commonjs_dependencies() -> None:
    source = dedent(
        """\
        import path from "node:path";
        import { UserService } from "./user-service.js";
        export { UserRepository } from "./repository.js";

        const config = require("./config.cjs");
        """,
    )

    root, _ = parse_javascript(source)

    imports = [
        node
        for node in find_nodes(
            root,
            ImportNode,
        )
        if isinstance(node, ImportNode)
    ]

    module_paths = {node.module_path for node in imports}

    assert module_paths == {
        "node:path",
        "./user-service.js",
        "./repository.js",
        "./config.cjs",
    }

    require_calls = [
        node
        for node in find_nodes(
            root,
            CallNode,
            name="require",
        )
    ]

    assert require_calls == []


def test_nested_function_keeps_parent_relationship() -> None:
    source = dedent(
        """\
        function outer() {
          function inner() {
            return 1;
          }

          return inner();
        }
        """,
    )

    root, _ = parse_javascript(source)

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


def test_jsx_arrow_component_is_parsed() -> None:
    source = dedent(
        """\
        const Greeting = ({ name }) => (
          <section>
            <h1>Hello {name}</h1>
          </section>
        );
        """,
    )

    root, _ = parse_javascript(
        source,
        file_path="Greeting.jsx",
    )

    component = find_single_node(
        root,
        FunctionNode,
        name="Greeting",
    )

    assert isinstance(component, FunctionNode)

    parameters = [
        node
        for node in find_nodes(
            component,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    ]

    assert len(parameters) == 1
    assert parameters[0].name == "{ name }"


def test_generator_function_is_marked() -> None:
    source = dedent(
        """\
        function* iterate(items) {
          yield* items;
        }
        """,
    )

    root, _ = parse_javascript(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="iterate",
    )

    assert isinstance(function, FunctionNode)
    assert function.is_generator is True


def test_javascript_byte_ranges_support_unicode_and_crlf() -> None:
    source = (
        "function tínhTổng(a, b) {\r\n"
        '  console.log("Tổng");\r\n'
        "  return a + b;\r\n"
        "}\r\n"
    )

    root, source_bytes = parse_javascript(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="tínhTổng",
    )

    function_text = source_bytes[function.start_byte : function.end_byte].decode(
        "utf-8"
    )

    assert function_text.startswith(
        "function tínhTổng",
    )
    assert function_text.endswith(
        "}",
    )
