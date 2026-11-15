"""CST toolkit of the JavaScript / TypeScript framework detectors (Hướng 2).

Same questions as ``languages/python/cst.py`` - which call sites, what object a receiver is and
where it was built, what string an argument evaluates to - answered on the javascript,
typescript and tsx grammars. Project names are followed through SCIP (scip-typescript); without
an index, bindings of the same file are searched.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from tree_sitter import Node, Query, QueryCursor, QueryError

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.rest_api_handler import join_url
from app.engine.scip.symbol import is_local_symbol
from app.engine.parser.languages import get_language_registry

type Site = dict[str, Node]
"""Captures of one ``sites.scm`` match, plus ``handler`` for decorator sites."""

type Bound = tuple[str, Node]
type Binding = tuple[str, str, Node]
"""``(form, path, node)``: ``value``, ``annotation`` or ``definition`` (a function or class
declaration, or a ``variable_declarator`` holding a function: the span UAST gives it)."""

type ObjectInfo = tuple[str | None, Bound | None, str | None]
"""``(kind, constructor, key)``, see :func:`resolve_object`."""

JS_LANGUAGES = ("javascript", "typescript", "tsx")
MAX_DEPTH = 8

FUNCTION_VALUES = frozenset(
    {"arrow_function", "function_expression", "function", "generator_function"}
)
DECLARATIONS = frozenset(
    {
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "abstract_class_declaration",
        "method_definition",
    }
)
_SCOPES = FUNCTION_VALUES | DECLARATIONS | {"class_body"}
_WRAPPERS = frozenset(
    {
        "parenthesized_expression",
        "await_expression",
        "as_expression",
        "satisfies_expression",
        "non_null_expression",
        "type_assertion",
    }
)
_NAME_NODES = frozenset({"identifier", "shorthand_property_identifier"})
_ENV = re.compile(r"^(?:process\.env|import\.meta\.env)\.([A-Za-z_]\w*)$")


@lru_cache
def _sites_query(language: str) -> Query:
    source = (Path(__file__).parent / "sites.scm").read_text(encoding="utf-8")
    grammar = get_language_registry().get_language(language)
    try:
        return Query(grammar, source)
    except (
        QueryError
    ):  # a grammar without decorators in class bodies: drop that pattern
        return Query(grammar, "; <receiver>" + source.split("; <receiver>", 1)[1])


def text(node: Node | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


def unwrap(node: Node | None) -> Node | None:
    """Strip parentheses, ``await`` and TypeScript assertions."""

    while node is not None and node.type in _WRAPPERS and node.named_children:
        node = node.named_children[0]
    return node


# ---------------------------------------------------------------------- sites and arguments


def iter_sites(
    ctx: ApiMapContext, path: str, method_names: frozenset[str]
) -> Iterator[Site]:
    """Decorator and call sites whose called name is in ``method_names``.

    The call inside a decorator also matches the bare-call pattern; decorator matches are
    sorted first and the call is not yielded twice. A decorator site gets ``handler``: the class
    member it decorates.
    """

    language = ctx.language_of(path)
    if language not in JS_LANGUAGES:
        return
    matches = QueryCursor(_sites_query(language)).matches(ctx.tree(path).root_node)
    matches.sort(
        key=lambda match: ("decorator" not in match[1], match[1]["site"][0].start_byte)
    )
    seen: set[tuple[int, int]] = set()
    for _, captures in matches:
        site = {name: nodes[0] for name, nodes in captures.items()}
        span = (site["site"].start_byte, site["site"].end_byte)
        if span in seen or text(site["method"]) not in method_names:
            continue
        seen.add(span)
        if "decorator" in site:
            member = _decorated_member(site["decorator"])
            if member is None:
                continue
            site["handler"] = member
        yield site


def _decorated_member(decorator: Node) -> Node | None:
    sibling = decorator.next_named_sibling
    while sibling is not None and sibling.type in ("decorator", "comment"):
        sibling = sibling.next_named_sibling
    return (
        sibling if sibling is not None and sibling.type == "method_definition" else None
    )


def arg(args: Node | None, position: int) -> Node | None:
    """Positional argument; ``None`` when absent or behind a spread (``...rest``)."""

    if args is None:
        return None
    positional: list[Node] = []
    for child in args.named_children:
        if child.type == "spread_element":
            break
        if child.type != "comment":
            positional.append(child)
    return (
        positional[position] if -len(positional) <= position < len(positional) else None
    )


def arguments(args: Node | None) -> list[Node]:
    return (
        [c for c in args.named_children if c.type != "comment"]
        if args is not None
        else []
    )


def object_property(node: Node | None, key: str) -> Node | None:
    """Value of ``key`` in an object literal: ``{ baseURL: x }``, ``{ "method": "PUT" }``, ``{ url }``."""

    node = unwrap(node)
    if node is None or node.type != "object":
        return None
    for child in node.named_children:
        if child.type == "pair":
            name = child.child_by_field_name("key")
            if name is not None and text(name).strip("\"'") == key:
                return child.child_by_field_name("value")
        elif child.type == "shorthand_property_identifier" and text(child) == key:
            return child
    return None


def constructor_property(
    constructor: Bound | None, position: int, key: str
) -> Bound | None:
    """Property of an options object passed to the call that built an object."""

    if constructor is None:
        return None
    path, call = constructor
    value = object_property(arg(call.child_by_field_name("arguments"), position), key)
    return (path, value) if value is not None else None


def scope_name(node: Node) -> str:
    """``ProductsClient.list`` / ``getUser`` / ``<module>`` for a node (definitions include their name)."""

    names: list[str] = []
    current: Node | None = node
    while current is not None:
        if current.type in DECLARATIONS:
            names.append(text(current.child_by_field_name("name")))
        elif current.type == "variable_declarator":
            value = current.child_by_field_name("value")
            if value is not None and value.type in FUNCTION_VALUES:
                names.append(text(current.child_by_field_name("name")))
        current = current.parent
    return ".".join(name for name in reversed(names) if name) or "<module>"


# ---------------------------------------------------------------------- bindings


def binding(ctx: ApiMapContext, path: str, node: Node | None) -> Binding | None:
    """What a name (``x``) or a member (``this.x``, ``mod.x``) is bound to; SCIP first."""

    return _bind(ctx, path, node)[2] if node is not None else None


def _bind(
    ctx: ApiMapContext, path: str, node: Node
) -> tuple[str | None, bool, Binding | None]:
    target = (
        node.child_by_field_name("property")
        if node.type == "member_expression"
        else node
    )
    if target is None:
        return None, False, None
    symbol = ctx.symbol_at(path, target.start_byte, target.end_byte)
    if symbol is not None:
        site = ctx.definition_site(symbol)
        if site is not None:
            return symbol, True, _binding_at(ctx, *site)
        if not is_local_symbol(symbol):
            return (
                symbol,
                False,
                None,
            )  # defined outside the project (or an unresolved import)
        # a document-local symbol without definition: the indexer gave up (`this.x` in untyped
        # JavaScript), the same-file search may still find it
    bound = _local_binding(ctx, path, node)
    return symbol, bound is not None, bound


def _binding_at(
    ctx: ApiMapContext, path: str, start_byte: int, end_byte: int
) -> Binding | None:
    """Climb from a definition identifier to the construct that binds it."""

    node: Node | None = ctx.tree(path).root_node.descendant_for_byte_range(
        start_byte, end_byte
    )
    while node is not None and node.parent is not None:
        parent = node.parent
        if parent.type == "member_expression" and _same(
            parent.child_by_field_name("property"), node
        ):
            node = parent  # this.client = ...
            continue
        if parent.type == "variable_declarator" and _same(
            parent.child_by_field_name("name"), node
        ):
            return _declarator_binding(path, parent)
        if parent.type in DECLARATIONS and _same(
            parent.child_by_field_name("name"), node
        ):
            return "definition", path, parent
        if parent.type == "assignment_expression" and _same(
            parent.child_by_field_name("left"), node
        ):
            right = parent.child_by_field_name("right")
            return ("value", path, right) if right is not None else None
        if parent.type in ("public_field_definition", "field_definition"):
            return _field_binding(path, parent)
        if parent.type in ("required_parameter", "optional_parameter"):
            annotation = parent.child_by_field_name("type")
            return ("annotation", path, annotation) if annotation is not None else None
        return None
    return None


def _same(a: Node | None, b: Node) -> bool:
    return a is not None and a.start_byte == b.start_byte and a.end_byte == b.end_byte


def _declarator_binding(path: str, declarator: Node) -> Binding | None:
    value = declarator.child_by_field_name("value")
    if value is None:
        annotation = declarator.child_by_field_name("type")
        return ("annotation", path, annotation) if annotation is not None else None
    if value.type in FUNCTION_VALUES:
        return "definition", path, declarator
    return "value", path, value


def _field_binding(path: str, field: Node) -> Binding | None:
    value = field.child_by_field_name("value")
    if value is not None:
        return (
            ("definition", path, field)
            if value.type in FUNCTION_VALUES
            else ("value", path, value)
        )
    annotation = field.child_by_field_name("type")
    return ("annotation", path, annotation) if annotation is not None else None


def _local_binding(ctx: ApiMapContext, path: str, node: Node) -> Binding | None:
    """Same-file fallback: enclosing scopes of a name, or the class of ``this.x``."""

    if node.type in _NAME_NODES:
        name = text(node)
        scope: Node | None = node.parent
        while scope is not None:
            if scope.type in FUNCTION_VALUES or scope.type in (
                "function_declaration",
                "method_definition",
            ):
                parameter = _parameter(scope, name)
                if parameter is not None:
                    annotation = parameter.child_by_field_name("type")
                    return (
                        ("annotation", path, annotation)
                        if annotation is not None
                        else None
                    )
                found = _last_binding(path, scope, name, node.start_byte)
                if found is not None:
                    return found
            elif scope.type == "program":
                return _last_binding(path, scope, name, node.start_byte)
            scope = scope.parent
        return None

    if (
        node.type == "member_expression"
        and text(node.child_by_field_name("object")) == "this"
    ):
        member = text(node.child_by_field_name("property"))
        body: Node | None = node.parent
        while body is not None and body.type != "class_body":
            body = body.parent
        return _class_member(path, body, member) if body is not None else None
    return None


def _parameter(function: Node, name: str) -> Node | None:
    parameters = function.child_by_field_name(
        "parameters"
    ) or function.child_by_field_name("parameter")
    if parameters is None:
        return None
    if parameters.type == "identifier":
        return parameters if text(parameters) == name else None
    for child in parameters.named_children:
        pattern = (
            child.child_by_field_name("pattern")
            or child.child_by_field_name("left")
            or child
        )
        if text(pattern) == name:
            return child
    return None


def _scope_nodes(scope: Node) -> Iterator[Node]:
    """Descendants of a scope, without entering nested functions and classes."""

    stack = list(reversed(scope.children))
    while stack:
        node = stack.pop()
        yield node
        if node.type not in _SCOPES:
            stack.extend(reversed(node.children))


def _last_binding(path: str, scope: Node, name: str, before: int) -> Binding | None:
    found: list[tuple[int, Binding]] = []
    for node in _scope_nodes(scope):
        if (
            node.type == "variable_declarator"
            and text(node.child_by_field_name("name")) == name
        ):
            bound = _declarator_binding(path, node)
            if bound is not None:
                found.append((node.start_byte, bound))
        elif (
            node.type in DECLARATIONS and text(node.child_by_field_name("name")) == name
        ):
            found.append((node.start_byte, ("definition", path, node)))
    earlier = [bound for start, bound in found if start < before]
    if earlier:
        return earlier[-1]
    return found[0][1] if found else None


def _class_member(path: str, body: Node, member: str) -> Binding | None:
    """A field ``x = ...``, a constructor ``this.x = ...`` or a parameter property ``private x: T``."""

    for child in body.named_children:
        if child.type in ("public_field_definition", "field_definition"):
            if (
                text(
                    child.child_by_field_name("name")
                    or child.child_by_field_name("property")
                )
                == member
            ):
                return _field_binding(path, child)
    for node in _scope_nodes_deep(body):
        if node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            if (
                left is not None
                and left.type == "member_expression"
                and text(left.child_by_field_name("object")) == "this"
                and text(left.child_by_field_name("property")) == member
            ):
                right = node.child_by_field_name("right")
                return ("value", path, right) if right is not None else None
        elif node.type == "required_parameter" and any(
            c.type == "accessibility_modifier" for c in node.children
        ):
            if text(node.child_by_field_name("pattern")) == member:
                annotation = node.child_by_field_name("type")
                return (
                    ("annotation", path, annotation) if annotation is not None else None
                )
    return None


def _scope_nodes_deep(body: Node) -> Iterator[Node]:
    stack = list(body.children)
    while stack:
        node = stack.pop(0)
        yield node
        if node.type not in ("class_declaration", "class"):
            stack.extend(node.children)


# ---------------------------------------------------------------------- objects


def resolve_object(
    ctx: ApiMapContext, path: str, node: Node | None, depth: int = 0
) -> ObjectInfo:
    """Kind, constructor and identity of the object an expression evaluates to.

    kind: qualified name of a module or export (``"axios"``, ``"express.Router"``,
        ``"@nestjs/core.NestFactory.create"``); a trailing ``()`` marks a value built by calling it
        (``"express()"``, ``"axios.create()"``). ``None`` when unknown.
    """

    node = unwrap(node)
    if node is None or depth > MAX_DEPTH:
        return None, None, None

    if node.type in _NAME_NODES or node.type == "member_expression":
        followed = _follow(ctx, path, node, depth)
        if followed is not None:
            return followed
        if node.type != "member_expression":
            imported = ctx.import_table(path).get(text(node))
            return (
                (imported, None, None) if imported is not None else (None, None, None)
            )
        base, _, _ = resolve_object(
            ctx, path, node.child_by_field_name("object"), depth + 1
        )
        if base is not None and not base.endswith("()"):
            return f"{base}.{text(node.child_by_field_name('property'))}", None, None
        return None, None, None

    if node.type in ("call_expression", "new_expression"):
        function = node.child_by_field_name("function") or node.child_by_field_name(
            "constructor"
        )
        if function is not None and text(function) == "require":  # require("axios")
            module = arg(node.child_by_field_name("arguments"), 0)
            return (
                (_string(ctx, path, module, depth) if module is not None else None),
                None,
                None,
            )
        callee, _, _ = resolve_object(ctx, path, function, depth + 1)
        if callee is not None and not callee.endswith("()"):
            return f"{callee}()", (path, node), None
        return None, None, None

    if node.type == "type_annotation":  # http: HttpClient
        inner = node.named_children[0] if node.named_children else None
        kind, _, _ = resolve_object(ctx, path, inner, depth + 1)
        return (f"{kind}()" if kind and not kind.endswith("()") else kind), None, None
    if node.type in ("type_identifier", "generic_type"):
        name = node.child_by_field_name("name") if node.type == "generic_type" else node
        imported = ctx.import_table(path).get(text(name))
        return imported, None, None

    return None, None, None


def _follow(ctx: ApiMapContext, path: str, node: Node, depth: int) -> ObjectInfo | None:
    """Object behind a project binding; ``None`` when the name is not bound in the project."""

    symbol, found, bound = _bind(ctx, path, node)
    if not found:
        return None
    key = symbol or (f"{bound[1]}:{bound[2].start_byte}" if bound is not None else None)
    if bound is None or bound[0] == "definition":
        return None, None, key
    kind, constructor, _ = resolve_object(ctx, bound[1], bound[2], depth + 1)
    return kind, constructor, key


def site_object(ctx: ApiMapContext, path: str, site: Site) -> ObjectInfo:
    """Kind of the receiver (or, for a bare call, of the called function); memoised per site.

    Tier A: when scip-typescript resolved the called name to a library (``node_modules`` present
    while indexing), its owner wins.
    """

    memo: dict[tuple[str, int, int], ObjectInfo] = ctx.memo.setdefault(
        "javascript.site_object", {}
    )
    key = (path, site["site"].start_byte, site["site"].end_byte)
    if key not in memo:
        kind, constructor, identity = resolve_object(
            ctx, path, site.get("receiver", site["method"])
        )
        method = site["method"]
        tier_a = (
            ctx.scip_owner(path, method.start_byte, method.end_byte)
            if "receiver" in site
            else None
        )
        memo[key] = (tier_a or kind, constructor, identity)
    return memo[key]


# ---------------------------------------------------------------------- strings


def _placeholder(expression: Node) -> str:
    name = text(expression).rsplit(".", 1)[-1]
    return "{" + name + "}" if re.fullmatch(r"[A-Za-z_$][\w$]*", name) else "{}"


def evaluate(
    ctx: ApiMapContext, path: str, node: Node | None, depth: int = 0
) -> str | None:
    """String value of an expression as a template; unknown parts become ``{name}`` placeholders,
    environment variables ``{$NAME}`` (their ``|| "default"`` / ``?? "default"`` when given)."""

    node = unwrap(node)
    if node is None or depth > MAX_DEPTH:
        return None
    kind = node.type
    if kind == "string":
        return _string(ctx, path, node, depth)
    if kind == "template_string":
        parts: list[str] = []
        for child in node.named_children:
            if child.type in ("string_fragment", "escape_sequence"):
                parts.append(text(child))
            elif child.type == "template_substitution":
                expression = child.named_children[0] if child.named_children else None
                value = evaluate(ctx, path, expression, depth + 1)
                parts.append(
                    value
                    if value is not None
                    else _placeholder(expression)
                    if expression
                    else "{}"
                )
        return "".join(parts)
    if kind == "binary_expression":
        return _binary(ctx, path, node, depth)
    if kind == "ternary_expression":
        branches = (
            evaluate(ctx, path, node.child_by_field_name(f), depth + 1)
            for f in ("consequence", "alternative")
        )
        return next((value for value in branches if value is not None), None)
    if kind == "member_expression" and (env := _ENV.match(text(node))):
        return "{$" + env.group(1) + "}"
    if kind in _NAME_NODES or kind == "member_expression":
        bound = binding(ctx, path, node)
        if bound is None or bound[0] != "value":
            return None
        return evaluate(ctx, bound[1], bound[2], depth + 1)
    if (
        kind == "new_expression"
        and text(node.child_by_field_name("constructor")) == "URL"
    ):
        args = node.child_by_field_name("arguments")  # new URL(path, base)
        return _urljoin(
            evaluate(ctx, path, arg(args, 1), depth + 1),
            evaluate(ctx, path, arg(args, 0), depth + 1),
        )
    if (
        kind == "call_expression"
        and text(node.child_by_field_name("function")) == "String"
    ):
        return evaluate(
            ctx, path, arg(node.child_by_field_name("arguments"), 0), depth + 1
        )
    return None


def _string(ctx: ApiMapContext, path: str, node: Node, depth: int) -> str | None:
    if node.type != "string":
        return evaluate(ctx, path, node, depth + 1)
    return "".join(
        text(c)
        for c in node.named_children
        if c.type in ("string_fragment", "escape_sequence")
    )


def _binary(ctx: ApiMapContext, path: str, node: Node, depth: int) -> str | None:
    operator = text(node.child_by_field_name("operator"))
    left = evaluate(ctx, path, node.child_by_field_name("left"), depth + 1)
    right = evaluate(ctx, path, node.child_by_field_name("right"), depth + 1)
    if operator == "+":
        if left is None and right is None:
            return None
        return (left or "{}") + (right or "{}")
    if operator in ("||", "??"):
        # process.env.X || "http://default": the default is what the code runs with locally
        if left is not None and left.startswith("{$") and right is not None:
            return right
        return left if left is not None else right
    return None


def _urljoin(base: str | None, url: str | None) -> str | None:
    if base is None or url is None:
        return url if base is None else base + "{}"
    if re.match(r"^[a-zA-Z][\w+.-]*://", url):
        return url
    if url.startswith("/"):
        host = re.match(r"^[a-zA-Z][\w+.-]*://[^/]*", base)
        return (host.group(0) if host else "") + url
    return join_url(base.rsplit("/", 1)[0] if not base.endswith("/") else base, url)
