"""Semantic tests for TypeScript and TSX UAST conversion."""

from collections.abc import Iterator
from textwrap import dedent

from tree_sitter import Query

from app.parser.languages import get_language_registry
from app.parser.languages.typescript.adapter import (
    get_tsx_query,
    get_typescript_query,
)
from app.parser.uast import (
    CallNode,
    FunctionNode,
    ImportNode,
    TypeDefinitionNode,
    UASTNode,
    VariableNode,
)


def parse_typescript(
    source: str,
    *,
    file_path: str = "sample.ts",
) -> tuple[UASTNode, bytes]:
    """Parse TypeScript or TSX source into UAST."""

    source_bytes = source.encode(
        "utf-8",
    )

    registry = get_language_registry()

    parser = registry.get_parser_for_file(
        file_path,
    )
    converter = registry.get_converter_for_file(
        file_path,
    )

    tree = parser.parse(
        source_bytes,
    )

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
        yield from walk_uast(
            child,
        )


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


def test_typescript_and_tsx_queries_compile() -> None:
    """The shared query must compile against both dialects."""

    assert isinstance(
        get_typescript_query(),
        Query,
    )
    assert isinstance(
        get_tsx_query(),
        Query,
    )


def test_typescript_root_contains_language_and_path() -> None:
    root, _ = parse_typescript(
        "const value: number = 1;\n",
        file_path="src/service.ts",
    )

    assert root.name == "src/service.ts"

    root_dict = root.to_dict()

    assert root_dict["path"] == "src/service.ts"
    assert root_dict["language"] == "typescript"


def test_interface_type_alias_and_enum() -> None:
    source = dedent(
        """\
        interface User extends Entity {
          readonly id: string;
        }

        type UserId = string | number;

        enum Role {
          Admin = "admin",
          User = "user",
        }
        """,
    )

    root, _ = parse_typescript(source)

    user = find_single_node(
        root,
        TypeDefinitionNode,
        name="User",
    )
    user_id = find_single_node(
        root,
        TypeDefinitionNode,
        name="UserId",
    )
    role = find_single_node(
        root,
        TypeDefinitionNode,
        name="Role",
    )

    assert isinstance(
        user,
        TypeDefinitionNode,
    )
    assert user.kind == "interface"
    assert user.base_types == [
        "Entity",
    ]

    assert isinstance(
        user_id,
        TypeDefinitionNode,
    )
    assert user_id.kind == "type_alias"
    assert user_id.metadata["aliased_type"] == "string | number"

    assert isinstance(
        role,
        TypeDefinitionNode,
    )
    assert role.kind == "enum"
    assert role.enum_values == [
        "Admin",
        "User",
    ]


def test_class_constructor_methods_field_and_modifiers() -> None:
    source = dedent(
        """\
        abstract class UserService<T>
          extends BaseService
          implements Repository<T>
        {
          private readonly version: string = "1";

          constructor(
            private readonly repository: Repository<T>,
          ) {}

          static async create(
            repository: Repository<User>,
          ): Promise<UserService<User>> {
            return new UserService(repository);
          }

          async find(
            id: UserId,
            limit: number = 10,
          ): Promise<T | null> {
            return this.repository.find(id, limit);
          }
        }
        """,
    )

    root, _ = parse_typescript(source)

    class_node = find_single_node(
        root,
        TypeDefinitionNode,
        name="UserService",
    )

    assert isinstance(
        class_node,
        TypeDefinitionNode,
    )
    assert class_node.kind == "class"
    assert class_node.is_abstract is True
    assert class_node.base_types == [
        "BaseService",
        "Repository<T>",
    ]

    version = find_single_node(
        class_node,
        VariableNode,
        name="version",
    )

    assert isinstance(
        version,
        VariableNode,
    )
    assert version.kind == "field"
    assert version.data_type == "string"
    assert version.initial_value == '"1"'
    assert version.visibility == "private"
    assert "readonly" in version.modifiers

    constructor = find_single_node(
        class_node,
        FunctionNode,
        name="constructor",
    )

    assert isinstance(
        constructor,
        FunctionNode,
    )
    assert constructor.kind == "constructor"

    constructor_parameters = {
        node.name: node
        for node in find_nodes(
            constructor,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    }

    repository = constructor_parameters["repository"]

    assert repository.data_type == "Repository<T>"
    assert repository.visibility == "private"
    assert "readonly" in repository.modifiers

    create_method = find_single_node(
        class_node,
        FunctionNode,
        name="create",
    )

    assert isinstance(
        create_method,
        FunctionNode,
    )
    assert create_method.kind == "method"
    assert create_method.is_static is True
    assert create_method.is_async is True
    assert create_method.return_type == "Promise<UserService<User>>"

    find_method = find_single_node(
        class_node,
        FunctionNode,
        name="find",
    )

    assert isinstance(
        find_method,
        FunctionNode,
    )
    assert find_method.is_async is True
    assert find_method.return_type == "Promise<T | null>"

    find_parameters = {
        node.name: node
        for node in find_nodes(
            find_method,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    }

    assert find_parameters["id"].data_type == "UserId"

    assert find_parameters["limit"].data_type == "number"

    assert find_parameters["limit"].initial_value == "10"


def test_typed_arrow_function_parameters_return_type_and_call() -> None:
    source = dedent(
        """\
        const loadUser = async (
          id: UserId,
          cache?: boolean,
        ): Promise<User> => {
          return api.users.get(id);
        };
        """,
    )

    root, _ = parse_typescript(source)

    function = find_single_node(
        root,
        FunctionNode,
        name="loadUser",
    )

    assert isinstance(
        function,
        FunctionNode,
    )
    assert function.kind == "function"
    assert function.is_async is True
    assert function.return_type == "Promise<User>"

    duplicate_variables = find_nodes(
        root,
        VariableNode,
        name="loadUser",
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
        "cache",
    }

    assert parameters["id"].data_type == "UserId"

    assert parameters["cache"].data_type == "boolean"

    assert parameters["cache"].metadata["optional"] is True

    call = find_single_node(
        function,
        CallNode,
        name="get",
    )

    assert isinstance(
        call,
        CallNode,
    )
    assert call.subject == "api.users"


def test_type_import_reexport_and_commonjs_dependency() -> None:
    source = dedent(
        """\
        import type { User } from "./types";
        import { Repository } from "./repository";
        export { UserService } from "./service";

        const config = require("./config");
        """,
    )

    root, _ = parse_typescript(source)

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
        "./types",
        "./repository",
        "./service",
        "./config",
    }

    require_calls = find_nodes(
        root,
        CallNode,
        name="require",
    )

    assert require_calls == []


def test_tsx_arrow_component_is_a_typed_function() -> None:
    source = dedent(
        """\
        type CardProps = {
          title: string;
          count?: number;
        };

        export const Card = ({
          title,
          count = 0,
        }: CardProps): JSX.Element => (
          <section data-count={count}>
            <h1>{title}</h1>
          </section>
        );
        """,
    )

    root, _ = parse_typescript(
        source,
        file_path="Card.tsx",
    )

    component = find_single_node(
        root,
        FunctionNode,
        name="Card",
    )

    assert isinstance(
        component,
        FunctionNode,
    )
    assert component.kind == "function"
    assert component.return_type == "JSX.Element"

    parameters = [
        node
        for node in find_nodes(
            component,
            VariableNode,
        )
        if isinstance(node, VariableNode) and node.kind == "parameter"
    ]

    assert len(parameters) == 1

    props = parameters[0]

    assert props.name is not None
    assert "title" in props.name
    assert "count = 0" in props.name
    assert props.data_type == "CardProps"

    root_dict = root.to_dict()

    assert root_dict["language"] == "typescript"
    assert root_dict["path"] == "Card.tsx"


def test_typescript_byte_ranges_support_unicode_and_crlf() -> None:
    source = (
        "function tínhTổng(a: number, b: number): number {\r\n  return a + b;\r\n}\r\n"
    )

    root, source_bytes = parse_typescript(
        source,
    )

    function = find_single_node(
        root,
        FunctionNode,
        name="tínhTổng",
    )

    function_text = source_bytes[function.start_byte : function.end_byte].decode(
        "utf-8",
    )

    assert function_text.startswith(
        "function tínhTổng",
    )
    assert function_text.endswith(
        "}",
    )
