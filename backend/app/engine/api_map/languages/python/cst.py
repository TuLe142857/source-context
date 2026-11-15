"""CST toolkit of the Python framework detectors (Hướng 2).

Answers, for an expression of a Python file: which call sites are there, what object does a
receiver denote and where was it built (``resolve_object``), and what string does an argument
evaluate to (``evaluate``). Resolution follows project names through SCIP, across files; without
an index it falls back to bindings of the same file.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from tree_sitter import Node, Query, QueryCursor

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.rest_api_handler import join_url
from app.engine.scip.symbol import is_local_symbol
from app.engine.parser.languages.python.adapter import get_language

type Site = dict[str, Node]
"""Captures of one ``sites.scm`` match: ``site``, ``method``, ``args``, maybe ``receiver`` / ``handler``."""

type Bound = tuple[str, Node]
"""A CST node and the path of its file: resolution routinely crosses files."""

type Binding = tuple[str, str, Node]
"""``(form, path, node)``; form is ``value`` (assigned expression), ``annotation`` (declared type)
or ``definition`` (``function_definition`` / ``class_definition``)."""

type ObjectInfo = tuple[str | None, Bound | None, str | None]
"""``(kind, constructor, key)``, see :func:`resolve_object`."""

MAX_DEPTH = 8
"""Bound on every recursive resolution; it also cuts cycles such as ``A = B; B = A``."""

INSTANCE_FACTORIES = {"requests.session": "requests.Session"}
"""Functions returning an instance of a known class."""

ENV_GETTERS = frozenset({"os.getenv", "os.environ.get", "os.environ.setdefault"})
URL_JOINS = frozenset({"urllib.parse.urljoin", "urlparse.urljoin"})
_SCOPES = ("function_definition", "class_definition", "lambda")


@lru_cache
def _sites_query() -> Query:
    return Query(
        get_language(),
        (Path(__file__).parent / "sites.scm").read_text(encoding="utf-8"),
    )


def text(node: Node | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------- sites and arguments


def iter_sites(
    ctx: ApiMapContext, path: str, method_names: frozenset[str]
) -> Iterator[Site]:
    """Decorator and call sites of a file whose called name is in ``method_names``.

    A decorator's ``call`` also matches the plain-call pattern, and that match completes before
    the decorator one, so decorator matches (pattern 0) are sorted first and their call is not
    yielded twice.
    """

    matches = QueryCursor(_sites_query()).matches(ctx.tree(path).root_node)
    matches.sort(key=lambda match: (match[0] != 0, match[1]["site"][0].start_byte))
    seen: set[tuple[int, int]] = set()
    for _, captures in matches:
        site = {name: nodes[0] for name, nodes in captures.items()}
        span = (site["site"].start_byte, site["site"].end_byte)
        if span in seen or text(site["method"]) not in method_names:
            continue
        seen.add(span)
        yield site


def arg(args: Node | None, position: int | None, keyword: str) -> Node | None:
    """Argument passed by ``keyword``, else at ``position``.

    ``None`` when absent, or when a ``*args`` makes positions unreliable (``**kwargs`` does not).
    """

    if args is None:
        return None
    positional: list[Node] = []
    unpacked = False
    for child in args.named_children:
        if child.type == "keyword_argument":
            if text(child.child_by_field_name("name")) == keyword:
                return child.child_by_field_name("value")
        elif child.type == "list_splat":
            unpacked = True
        elif child.type not in ("comment", "dictionary_splat"):
            positional.append(child)
    if position is None or unpacked or position >= len(positional):
        return None
    return positional[position]


def constructor_arg(constructor: Bound | None, keyword: str) -> Bound | None:
    """Keyword argument of the call that built an object, with the call's file."""

    if constructor is None:
        return None
    path, call = constructor
    value = arg(call.child_by_field_name("arguments"), None, keyword)
    return (path, value) if value is not None else None


def scope_name(node: Node) -> str:
    """``UserClient.fetch`` for a node inside that method (a definition includes its own name)."""

    names: list[str] = []
    current: Node | None = node
    while current is not None:
        if current.type in ("function_definition", "class_definition"):
            names.append(text(current.child_by_field_name("name")))
        current = current.parent
    return ".".join(reversed(names)) or "<module>"


# ---------------------------------------------------------------------- bindings


def binding(ctx: ApiMapContext, path: str, node: Node | None) -> Binding | None:
    """What a name (``x``) or an attribute (``self.x``, ``module.x``) is bound to.

    SCIP is authoritative when it has an occurrence for the name: its definition site, or
    nothing for names defined outside the project. Without one, same-file bindings are searched.
    """

    return _bind(ctx, path, node)[2] if node is not None else None


def _bind(
    ctx: ApiMapContext, path: str, node: Node
) -> tuple[str | None, bool, Binding | None]:
    """``(symbol, resolved, binding)``; ``resolved`` is False when nothing could tell."""

    target = node.child_by_field_name("attribute") if node.type == "attribute" else node
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
        if parent.type in ("attribute", "as_pattern_target"):
            node = parent  # self.x = ... / with ... as x
            continue
        if parent.type == "assignment":
            left = parent.child_by_field_name("left")
            if left is None or left.id != node.id:
                return None
            return _assignment_binding(path, parent)
        if parent.type == "as_pattern" and node.type == "as_pattern_target":
            return "value", path, parent.named_children[0]
        if parent.type in ("typed_parameter", "typed_default_parameter"):
            annotation = parent.child_by_field_name("type")
            return ("annotation", path, annotation) if annotation is not None else None
        if parent.type in ("function_definition", "class_definition"):
            return "definition", path, parent
        return None
    return None


def _assignment_binding(path: str, assignment: Node) -> Binding | None:
    right = assignment.child_by_field_name("right")
    if right is not None:
        return "value", path, right
    annotation = assignment.child_by_field_name("type")
    return ("annotation", path, annotation) if annotation is not None else None


def _local_binding(ctx: ApiMapContext, path: str, node: Node) -> Binding | None:
    """Same-file fallback: the enclosing scopes of a name, or the class of ``self.x``."""

    if node.type == "identifier":
        name = text(node)
        scope: Node | None = node.parent
        while scope is not None:
            if scope.type in ("function_definition", "lambda"):
                if _is_parameter(scope, name):
                    return _parameter_binding(path, scope, name)
                found = _last_binding(path, scope, name, node.start_byte)
                if found is not None:
                    return found
            elif scope.type == "module":
                return _last_binding(path, scope, name, node.start_byte)
            scope = scope.parent
        return None

    if node.type == "attribute":
        owner = node.child_by_field_name("object")
        if owner is None or text(owner) not in ("self", "cls"):
            return None
        attribute = text(node.child_by_field_name("attribute"))
        cls: Node | None = node.parent
        while cls is not None and cls.type != "class_definition":
            cls = cls.parent
        return _class_attribute(path, cls, attribute) if cls is not None else None
    return None


def _is_parameter(function: Node, name: str) -> bool:
    parameters = function.child_by_field_name("parameters")
    return parameters is not None and any(
        text(_parameter_name(child)) == name for child in parameters.named_children
    )


def _parameter_name(parameter: Node) -> Node | None:
    if parameter.type == "identifier":
        return parameter
    named = parameter.child_by_field_name("name")
    return (
        named
        if named is not None
        else (parameter.named_children[0] if parameter.named_children else None)
    )


def _parameter_binding(path: str, function: Node, name: str) -> Binding | None:
    parameters = function.child_by_field_name("parameters")
    for child in parameters.named_children if parameters is not None else []:
        if text(_parameter_name(child)) == name and child.type in (
            "typed_parameter",
            "typed_default_parameter",
        ):
            annotation = child.child_by_field_name("type")
            return ("annotation", path, annotation) if annotation is not None else None
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
    """Last binding of ``name`` in ``scope`` before ``before``, else its first one after."""

    found: list[tuple[int, Binding]] = []
    for node in _scope_nodes(scope):
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            if left is not None and left.type == "identifier" and text(left) == name:
                bound = _assignment_binding(path, node)
                if bound is not None:
                    found.append((node.start_byte, bound))
        elif node.type == "as_pattern":
            alias = node.child_by_field_name("alias")
            if alias is not None and text(alias) == name and node.named_children:
                found.append((node.start_byte, ("value", path, node.named_children[0])))
        elif (
            node.type in ("function_definition", "class_definition")
            and text(node.child_by_field_name("name")) == name
        ):
            found.append((node.start_byte, ("definition", path, node)))
    earlier = [bound for start, bound in found if start < before]
    if earlier:
        return earlier[-1]
    return found[0][1] if found else None


def _class_attribute(path: str, cls: Node, attribute: str) -> Binding | None:
    """``x = ...`` in the class body, else the first ``self.x = ...`` in one of its methods."""

    body = cls.child_by_field_name("body")
    if body is None:
        return None
    for statement in body.named_children:
        if statement.type == "expression_statement" and statement.named_children:
            assignment = statement.named_children[0]
            left = (
                assignment.child_by_field_name("left")
                if assignment.type == "assignment"
                else None
            )
            if (
                left is not None
                and left.type == "identifier"
                and text(left) == attribute
            ):
                return _assignment_binding(path, assignment)
    stack = list(body.children)
    while stack:
        node = stack.pop(0)
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            if (
                left is not None
                and left.type == "attribute"
                and text(left.child_by_field_name("object")) == "self"
                and text(left.child_by_field_name("attribute")) == attribute
            ):
                return _assignment_binding(path, node)
        if node.type != "class_definition":
            stack.extend(node.children)
    return None


# ---------------------------------------------------------------------- objects


def resolve_object(
    ctx: ApiMapContext, path: str, node: Node | None, depth: int = 0
) -> ObjectInfo:
    """Kind, constructor and identity of the object an expression evaluates to.

    kind: qualified name of a module or class (``"httpx"``, ``"fastapi.APIRouter"``); a trailing
        ``()`` marks an instance (``"fastapi.APIRouter()"``). ``None`` when unknown.
    constructor: the call that built the instance, to read ``prefix=`` / ``base_url=``.
    key: identity shared by every reference to the object - its SCIP symbol when it has one -
        so a router decorated in one file and included in another is the same router.
    """

    if node is None or depth > MAX_DEPTH:
        return None, None, None
    if node.type in ("parenthesized_expression", "await"):
        return resolve_object(
            ctx,
            path,
            node.named_children[0] if node.named_children else None,
            depth + 1,
        )

    if node.type in ("identifier", "attribute"):
        followed = _follow(ctx, path, node, depth)
        if followed is not None:
            return followed
        if node.type == "identifier":
            imported = ctx.import_table(path).get(text(node))
            return (
                (imported, None, None) if imported is not None else (None, None, None)
            )
        base, _, _ = resolve_object(
            ctx, path, node.child_by_field_name("object"), depth + 1
        )
        if base is not None and not base.endswith("()"):
            return f"{base}.{text(node.child_by_field_name('attribute'))}", None, None
        return None, None, None

    if node.type == "call":
        callee, _, _ = resolve_object(
            ctx, path, node.child_by_field_name("function"), depth + 1
        )
        callee = INSTANCE_FACTORIES.get(callee or "", callee)
        if callee is not None and not callee.endswith("()"):
            return f"{callee}()", (path, node), None
        return None, None, None

    if node.type == "type":  # annotation `client: httpx.Client`
        inner = node.named_children[0] if node.named_children else None
        kind, _, _ = resolve_object(ctx, path, inner, depth + 1)
        return (f"{kind}()" if kind and not kind.endswith("()") else kind), None, None

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
    """Tier A kind when SCIP knows the called name, Tier B for everything else; memoised per site.

    For a bare call (pattern 2) the kind is the qualname of the called function itself
    (``urllib.request.urlopen``); frameworks tell the two apart with ``"receiver" in site``.
    """

    memo: dict[tuple[str, int, int], ObjectInfo] = ctx.memo.setdefault(
        "python.site_object", {}
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
    return "{" + name + "}" if re.fullmatch(r"[A-Za-z_]\w*", name) else "{}"


def evaluate(
    ctx: ApiMapContext, path: str, node: Node | None, depth: int = 0
) -> str | None:
    """String value of an expression as a template; unknown parts become ``{name}`` placeholders.

    ``None`` when nothing at all is known (a bare parameter, the result of an arbitrary call).
    """

    if node is None or depth > MAX_DEPTH:
        return None
    kind = node.type
    if kind == "string":
        return _string(ctx, path, node, depth)
    if kind == "concatenated_string":
        return "".join(
            evaluate(ctx, path, part, depth + 1) or "{}" for part in node.named_children
        )
    if kind == "binary_operator":
        return _binary(ctx, path, node, depth)
    if kind == "parenthesized_expression":
        return evaluate(
            ctx,
            path,
            node.named_children[0] if node.named_children else None,
            depth + 1,
        )
    if (
        kind == "conditional_expression"
    ):  # `a if c else b`: the first branch that is known
        branches = (
            evaluate(ctx, path, child, depth + 1) for child in node.named_children[::2]
        )
        return next((value for value in branches if value is not None), None)
    if kind in ("identifier", "attribute"):
        bound = binding(ctx, path, node)
        if bound is None or bound[0] != "value":
            return None
        return evaluate(ctx, bound[1], bound[2], depth + 1)
    if kind == "call":
        return _call(ctx, path, node, depth)
    if kind == "subscript":  # os.environ["X"]
        value, _, _ = resolve_object(
            ctx, path, node.child_by_field_name("value"), depth + 1
        )
        if value == "os.environ":
            name = evaluate(ctx, path, node.child_by_field_name("subscript"), depth + 1)
            return "{$" + name + "}" if name else None
    return None


def _string(ctx: ApiMapContext, path: str, node: Node, depth: int) -> str:
    parts: list[str] = []
    for child in node.named_children:
        if child.type in ("string_content", "escape_sequence"):
            parts.append(text(child))
        elif child.type == "interpolation":
            expression = child.child_by_field_name("expression")
            if expression is None:
                parts.append("{}")
                continue
            parts.append(
                evaluate(ctx, path, expression, depth + 1) or _placeholder(expression)
            )
    return "".join(parts)


def _binary(ctx: ApiMapContext, path: str, node: Node, depth: int) -> str | None:
    operator = node.child_by_field_name("operator")
    left = evaluate(ctx, path, node.child_by_field_name("left"), depth + 1)
    if operator is not None and operator.type == "+":
        right = evaluate(ctx, path, node.child_by_field_name("right"), depth + 1)
        if left is None and right is None:
            return None
        return (left or "{}") + (right or "{}")
    if operator is not None and operator.type == "%" and left is not None:
        return re.sub(r"%(?:\([^)]*\))?[-+ #0]*\d*(?:\.\d+)?[sdifr]", "{}", left)
    return None


def _call(ctx: ApiMapContext, path: str, node: Node, depth: int) -> str | None:
    function = node.child_by_field_name("function")
    args = node.child_by_field_name("arguments")
    if function is None:
        return None

    if (
        function.type == "attribute"
        and text(function.child_by_field_name("attribute")) == "format"
    ):
        base = evaluate(ctx, path, function.child_by_field_name("object"), depth + 1)
        if base is None:
            return None
        return re.sub(
            r"\{([^{}]*)\}",
            lambda m: "{" + m.group(1) + "}" if m.group(1).isidentifier() else "{}",
            base,
        )

    name = text(function)
    if name == "str":
        return evaluate(ctx, path, arg(args, 0, "object"), depth + 1)

    callee, _, _ = resolve_object(ctx, path, function, depth + 1)
    if callee in ENV_GETTERS:
        default = evaluate(ctx, path, arg(args, 1, "default"), depth + 1)
        if default is not None:
            return default
        env = evaluate(ctx, path, arg(args, 0, "key"), depth + 1)
        return "{$" + env + "}" if env else None
    if callee in URL_JOINS:
        return _urljoin(
            evaluate(ctx, path, arg(args, 0, "base"), depth + 1),
            evaluate(ctx, path, arg(args, 1, "url"), depth + 1),
        )
    if name == "Field" or (callee or "").endswith(
        ".Field"
    ):  # pydantic field with a default
        return evaluate(ctx, path, arg(args, 0, "default"), depth + 1)
    return None


def _urljoin(base: str | None, url: str | None) -> str | None:
    """RFC 3986 merge, enough for templates: an absolute-path reference keeps only the host."""

    if base is None or url is None:
        return url if base is None else base + "{}"
    if re.match(r"^[a-zA-Z][\w+.-]*://", url):
        return url
    if url.startswith("/"):
        host = re.match(r"^[a-zA-Z][\w+.-]*://[^/]*", base)
        return (host.group(0) if host else "") + url
    return join_url(base.rsplit("/", 1)[0] if not base.endswith("/") else base, url)
