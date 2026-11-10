"""Hướng 1 — text pattern: regex rules over UAST nodes and their source text.

The engine knows no framework and no language. A language contributes a rule table
(``languages/<language>/rest_patterns.py``); evidence is purely textual - a verb-like name, a
URL-like argument, a client-like receiver - hence the lower confidence. Framework detections
override these on the same anchor (``build.merge_detections``).

Only fields every language's UAST has are read: ``FunctionNode.decorators``, ``CallNode.name /
subject`` and span, ``VariableNode.initial_value``, ``ImportNode.module_path``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from app.engine.parser.uast import (
    CallNode,
    FunctionNode,
    ImportNode,
    TypeDefinitionNode,
    UASTNode,
    VariableNode,
)

from .context import ApiMapContext, walk
from .handlers.api_handler import Detection
from .handlers.rest_api_handler import RestApiHandler

logger = logging.getLogger(__name__)

type Patterns = dict[str, Any]
"""A language's rule table, see ``languages/python/rest_patterns.py``."""

type Lookup = Callable[[str], str | None]
"""Name -> known string value, in the scope of one node."""

type Scope = dict[str, Any]
"""Facts about one file: constants, router prefixes, framework and library hints, parents."""

MAX_CALL_CONFIDENCE = 0.8
"""Pattern detections always stay below framework ones."""


def detect(
    handler: RestApiHandler, ctx: ApiMapContext, paths: list[str], patterns: Patterns
) -> list[Detection]:
    """Endpoints and calls of ``paths`` found by the rules of ``patterns``."""

    detections: list[Detection] = []
    for path in paths:
        try:
            nodes = list(walk(ctx.uast(path)))
        except OSError:
            logger.warning("Cannot read %s, skipping", path)
            continue
        scope = _file_scope(nodes, patterns)
        functions = {
            node.name: node
            for node in nodes
            if isinstance(node, FunctionNode) and node.name
        }
        for node in nodes:
            if isinstance(node, FunctionNode):
                for decorator in node.decorators:
                    detections += _decorator_endpoints(
                        handler, ctx, path, node, decorator, scope, patterns
                    )
            elif isinstance(node, CallNode) and node.name:
                # a call registering a route (`app.get("/x", handler)`) is not a request
                detections += _call_endpoints(
                    handler, ctx, path, node, scope, functions, patterns
                ) or _calls(handler, ctx, path, node, scope, patterns)
    return detections


# ---------------------------------------------------------------------- text helpers


def _scan(text: str, on_depth0: Callable[[int, str], None]) -> None:
    """Walk ``text`` outside string literals, calling ``on_depth0(index, char)`` at bracket depth 0
    (an opening bracket is reported before entering it)."""

    depth, quote, index = 0, "", 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 1
            elif text.startswith(quote, index):
                index += len(quote) - 1
                quote = ""
        elif char in "\"'`":
            quote = (
                text[index : index + 3]
                if text[index : index + 3] in ('"""', "'''")
                else char
            )
            index += len(quote) - 1
        else:
            if depth == 0:
                on_depth0(index, char)
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth = max(depth - 1, 0)
        index += 1


def call_arguments(text: str) -> str:
    """Text between the last depth-0 ``(`` and the closing ``)``: the arguments of *this* call.

    The text of a call always ends with its own argument list, so this is right even when the
    callee contains another call (``get(x).get("/y")``).
    """

    opening: list[int] = []
    _scan(text, lambda index, char: opening.append(index) if char == "(" else None)
    if not opening:
        return ""
    return text[opening[-1] + 1 : text.rfind(")")]


def _split_top_level(text: str, separator: str) -> list[str]:
    """Split on ``separator`` at depth 0, outside strings."""

    cuts: list[int] = []
    _scan(text, lambda index, char: cuts.append(index) if char == separator else None)
    parts, start = [], 0
    for cut in cuts:
        parts.append(text[start:cut])
        start = cut + 1
    parts.append(text[start:])
    return parts


def split_arguments(
    arguments: str, patterns: Patterns
) -> tuple[list[str], dict[str, str]]:
    """Positional and keyword arguments; unpacked ones (``*a``, ``**kw``) are dropped."""

    positional: list[str] = []
    keyword: dict[str, str] = {}
    for part in (piece.strip() for piece in _split_top_level(arguments, ",")):
        if not part:
            continue
        if match := patterns["keyword"].match(part):
            keyword[match.group(1)] = match.group(2).strip()
        elif not part.startswith("*"):
            positional.append(part)
    return positional, keyword


def _placeholder(expression: str) -> str:
    """``self.base_url`` -> ``{base_url}``; anything not name-like -> ``{}``."""

    name = expression.strip().rsplit(".", 1)[-1]
    return "{" + name + "}" if re.fullmatch(r"[A-Za-z_]\w*", name) else "{}"


def evaluate_text(expression: str, lookup: Lookup, patterns: Patterns) -> str | None:
    """Template of a string expression from its text: literals, interpolations, names, ``+``.

    Calls, subscripts, ``%`` and ``.format`` are beyond what a regex reads safely: ``None``.
    """

    result: list[str] = []
    for part in (
        piece.strip() for piece in _split_top_level(expression, patterns["concat"])
    ):
        if match := patterns["string"].fullmatch(part):
            body = match.group("body")
            if _interpolates(match, patterns):
                body = patterns["hole"].sub(
                    lambda hole: (
                        lookup(hole.group(1).strip()) or _placeholder(hole.group(1))
                    ),
                    body,
                )
            result.append(body)
        elif patterns["identifier"].fullmatch(part):
            result.append(lookup(part) or _placeholder(part))
        else:
            return None
    return "".join(result) if result else None


def _interpolates(match: re.Match[str], patterns: Patterns) -> bool:
    """f-strings (a prefix letter) or template literals (a quote character)."""

    flag = patterns.get("interpolating_prefix", "")
    prefix = (match.group("prefix") or "").lower()
    return bool(flag and flag in prefix) or match.group("quote") in patterns.get(
        "interpolating_quotes", ()
    )


def _pick(
    positional: list[str], keyword: dict[str, str], where: tuple[int, str]
) -> str | None:
    index, name = where
    if name in keyword:
        return keyword[name]
    return positional[index] if index < len(positional) else None


def _object_property(text: str | None, key: str) -> str | None:
    """Value text of ``key`` in an object/dict literal text: ``{ method: "PUT" }``."""

    if text is None or not text.strip().startswith("{"):
        return None
    for part in _split_top_level(text.strip()[1:-1], ","):
        name, separator, value = part.partition(":")
        if separator and name.strip().strip("\"'") == key:
            return value.strip()
        if not separator and part.strip() == key:  # shorthand `{ url }`
            return key
    return None


def _argument(
    positional: list[str], keyword: dict[str, str], rule: dict[str, Any], name: str
) -> str | None:
    """Text of the ``name`` argument of a rule: ``<name>_arg`` (position, keyword) or
    ``<name>_option`` (position of an options object, property)."""

    if f"{name}_option" in rule:
        index, key = rule[f"{name}_option"]
        value = _object_property(
            positional[index] if index < len(positional) else None, key
        )
        if value is not None or f"{name}_arg" not in rule:
            return value
    if f"{name}_arg" in rule:
        return _pick(positional, keyword, rule[f"{name}_arg"])
    return None


def _string_list(text: str, patterns: Patterns) -> list[str]:
    """Literal strings of a list/tuple text: ``["GET", "POST"]`` -> ``["GET", "POST"]``."""

    inner = text.strip()[1:-1] if text.strip()[:1] in "[(" else text
    values = []
    for part in (piece.strip() for piece in _split_top_level(inner, ",")):
        if match := patterns["string"].fullmatch(part):
            values.append(match.group("body"))
    return values


# ---------------------------------------------------------------------- file scope


def _file_scope(nodes: list[UASTNode], patterns: Patterns) -> Scope:
    """Constants, router prefixes and hints of one file."""

    parent = {child.id: node for node in nodes for child in node.children}
    modules = [
        node.module_path
        for node in nodes
        if isinstance(node, ImportNode) and node.module_path
    ]
    # `fastapi.routing` -> fastapi; `@nestjs/common` and `node-fetch` stay whole
    imports = set(modules) | {module.lstrip(".").split(".")[0] for module in modules}
    scope: Scope = {
        "parent": parent,
        "imports": imports,
        "framework": next(
            (
                patterns["frameworks"][m]
                for m in sorted(imports)
                if m in patterns["frameworks"]
            ),
            None,
        ),
        "http_library": next(
            (m for m in sorted(imports) if m in patterns["http_libraries"]), None
        ),
        "constants": {},
        "inits": {},
        "prefixes": {},
    }

    variables = [
        node
        for node in nodes
        if isinstance(node, VariableNode)
        and node.kind in ("variable", "constant")
        and node.name
        and node.initial_value
    ]
    for variable in variables:
        scope["inits"][(_enclosing_function(scope, variable), variable.name)] = (
            variable.initial_value or ""
        ).strip()
    for _ in range(2):  # constants that use constants (BASE + "/x") need a second pass
        for variable in variables:
            value = _evaluate_value(
                variable.initial_value or "", _lookup(scope, variable), patterns
            )
            if value is not None:
                scope["constants"][
                    (_enclosing_function(scope, variable), variable.name)
                ] = value

    router_constructor: re.Pattern[str] | None = patterns.get("router_constructor")
    if (
        router_constructor is None
    ):  # no router carries a prefix in this language (Express)
        return scope
    for variable in variables:
        value = (variable.initial_value or "").strip()
        if not router_constructor.match(value):
            continue
        _, keyword = split_arguments(call_arguments(value), patterns)
        for name in patterns["router_prefix_keywords"]:
            if name in keyword:
                prefix = evaluate_text(
                    keyword[name], _lookup(scope, variable), patterns
                )
                if prefix is not None:
                    scope["prefixes"][variable.name] = prefix
    return scope


def _evaluate_value(value: str, lookup: Lookup, patterns: Patterns) -> str | None:
    """A variable's initial value: a string expression, or an env lookup (default first)."""

    value = value.strip()
    if "env_expression" in patterns and (
        env := patterns["env_expression"].match(value)
    ):
        # process.env.X || "default"
        default = env.group("default")
        result = evaluate_text(default, lookup, patterns) if default else None
        return result if result is not None else "{$" + env.group("name") + "}"
    if "env_getter" in patterns and patterns["env_getter"].match(value):
        positional, keyword = split_arguments(call_arguments(value), patterns)
        default = _pick(positional, keyword, (1, "default"))
        if (
            default is not None
            and (result := evaluate_text(default, lookup, patterns)) is not None
        ):
            return result
        name = _pick(positional, keyword, (0, "key"))
        env = evaluate_text(name, lookup, patterns) if name is not None else None
        return "{$" + env + "}" if env else None
    return evaluate_text(value, lookup, patterns)


def _enclosing_function(scope: Scope, node: UASTNode) -> str | None:
    """Id of the nearest enclosing ``FunctionNode`` (ancestors only), ``None`` at module level."""

    current = scope["parent"].get(node.id)
    while current is not None:
        if isinstance(current, FunctionNode):
            return current.id
        current = scope["parent"].get(current.id)
    return None


def _lookup(scope: Scope, node: UASTNode) -> Lookup:
    """Constants visible from ``node``: its enclosing function's first, then the module's."""

    return _scoped(scope, node, "constants")


def _scoped(scope: Scope, node: UASTNode, table: str) -> Lookup:
    function_id = _enclosing_function(scope, node)
    values: dict[tuple[str | None, str], str] = scope[table]

    def lookup(name: str) -> str | None:
        return values.get((function_id, name)) or values.get((None, name))

    return lookup


def _qualified_name(scope: Scope, node: UASTNode) -> str:
    """``UserClient.fetch`` for a node inside that method (the node itself included)."""

    names: list[str] = []
    current: UASTNode | None = node
    while current is not None:
        if isinstance(current, FunctionNode | TypeDefinitionNode) and current.name:
            names.append(current.name)
        current = scope["parent"].get(current.id)
    return ".".join(reversed(names)) or "<module>"


# ---------------------------------------------------------------------- endpoints


def _methods(
    verb: str | None, keyword: dict[str, str], rule: dict[str, Any], patterns: Patterns
) -> list[str]:
    """Verb in the decorator name, else the methods keyword, else the rule's default."""

    if verb:
        return ["*" if verb.upper() == "ALL" else verb.upper()]
    listed = keyword.get(rule.get("methods_kw", ""))
    if listed is not None:
        methods = [method.upper() for method in _string_list(listed, patterns)]
        if methods:
            return methods
    return list(rule.get("default_methods", ("GET",)))


def _route_path(local: str | None, rule: dict[str, Any]) -> str | None:
    if local is None:
        return None
    if local == "" or local.startswith("/"):
        return local
    return "/" + local if rule.get("relative_path") else None


def _join(prefix: str, local: str, rule: dict[str, Any]) -> str:
    """Concatenation (FastAPI, Express), or segment join (NestJS: "accounts" + ":id")."""

    if not rule.get("join_segments"):
        return prefix + local
    parts = [part.strip("/") for part in (prefix, local) if part.strip("/")]
    return "/" + "/".join(parts)


def _class_prefix(
    scope: Scope, function: FunctionNode, rule: dict[str, Any], patterns: Patterns
) -> str | None:
    """Prefix a decorator of the enclosing class gives (NestJS ``@Controller("users")``)."""

    owner = scope["parent"].get(function.id)
    if "class_prefix" not in rule or not isinstance(owner, TypeDefinitionNode):
        return None
    for decorator in owner.decorators:
        if not rule["class_prefix"].match(decorator):
            continue
        positional, keyword = split_arguments(call_arguments(decorator), patterns)
        text = positional[0] if positional else None
        text = _object_property(text, "path") or text
        if text is None:
            return ""
        return evaluate_text(text, _lookup(scope, owner), patterns)
    return None


def _decorator_endpoints(
    handler: RestApiHandler,
    ctx: ApiMapContext,
    path: str,
    function: FunctionNode,
    decorator: str,
    scope: Scope,
    patterns: Patterns,
) -> list[Detection]:
    for rule in patterns["endpoint_decorators"]:
        match = rule["match"].match(decorator)
        if match is None:
            continue
        positional, keyword = split_arguments(call_arguments(decorator), patterns)
        path_text = _argument(positional, keyword, rule, "path")
        local = _route_path(
            evaluate_text(path_text, _lookup(scope, function), patterns)
            if path_text is not None
            else "",
            rule,
        )
        if local is None:
            return []
        prefix = _class_prefix(scope, function, rule, patterns)
        if prefix is None:
            prefix = scope["prefixes"].get(match.groupdict().get("receiver") or "", "")
        full = _join(prefix, local, rule)
        name = _qualified_name(scope, function)
        anchor = (path, function.start_byte, function.end_byte)
        return [
            (
                handler.endpoint_node(
                    ctx,
                    method=method,
                    path=full,
                    framework=scope["framework"],
                    raw=path_text,
                    file=path,
                    handler_name=name,
                    detector="pattern",
                    rule=rule["id"],
                    confidence=rule["confidence"],
                ),
                anchor,
            )
            for method in _methods(
                match.groupdict().get("verb"), keyword, rule, patterns
            )
        ]
    return []


def _call_endpoints(
    handler: RestApiHandler,
    ctx: ApiMapContext,
    path: str,
    node: CallNode,
    scope: Scope,
    functions: dict[str, FunctionNode],
    patterns: Patterns,
) -> list[Detection]:
    for rule in patterns["endpoint_calls"]:
        if not rule["name"].fullmatch(node.name or ""):
            continue
        if (
            rule.get("requires_import")
            and rule["requires_import"] not in scope["imports"]
        ):
            continue
        if "receiver" in rule and not rule["receiver"].search(node.subject or ""):
            continue
        text = ctx.text(path, node.start_byte, node.end_byte)
        positional, keyword = split_arguments(call_arguments(text), patterns)
        if rule.get("requires_handler_arg") and not (
            len(positional) >= 2 and patterns["handler_like"].match(positional[-1])
        ):
            continue
        path_text = _argument(positional, keyword, rule, "path")
        if path_text is None:
            return []
        local = _route_path(
            evaluate_text(path_text, _lookup(scope, node), patterns), rule
        )
        if local is None:
            return []
        handler_text = _argument(positional, keyword, rule, "handler")
        target = functions.get(handler_text.strip()) if handler_text else None
        full = _join(scope["prefixes"].get(node.subject or "", ""), local, rule)
        # an inline handler has no FunctionNode: the route hangs on its registering call
        anchor = (
            (path, target.start_byte, target.end_byte)
            if target is not None
            else (path, node.start_byte, node.end_byte)
        )
        verb = node.name if rule.get("method_from_name") else None
        return [
            (
                handler.endpoint_node(
                    ctx,
                    method=method,
                    path=full,
                    framework=scope["framework"],
                    raw=path_text,
                    file=path,
                    handler_name=_qualified_name(scope, target)
                    if target is not None
                    else handler_text,
                    detector="pattern",
                    rule=rule["id"],
                    confidence=rule["confidence"],
                ),
                anchor,
            )
            for method in _methods(verb, keyword, rule, patterns)
        ]
    return []


# ---------------------------------------------------------------------- calls


def _calls(
    handler: RestApiHandler,
    ctx: ApiMapContext,
    path: str,
    node: CallNode,
    scope: Scope,
    patterns: Patterns,
) -> list[Detection]:
    for rule in patterns["calls"]:
        if not rule["name"].fullmatch(node.name or ""):
            continue
        if "receiver" in rule and not rule["receiver"].search(node.subject or ""):
            continue
        text = ctx.text(path, node.start_byte, node.end_byte)
        positional, keyword = split_arguments(call_arguments(text), patterns)
        url_text = _argument(positional, keyword, rule, "url")
        lookup = _lookup(scope, node)
        url = (
            evaluate_text(url_text, lookup, patterns) if url_text is not None else None
        )
        if url is None or not patterns["url_like"].match(url):
            return []
        confidence = _call_confidence(ctx, path, node, url, scope, rule, patterns)
        if confidence is None:
            return []
        call = handler.call_node(
            ctx,
            method=_call_method(node, positional, keyword, rule, lookup, patterns),
            url=url,
            library=scope["http_library"],
            raw=url_text,
            file=path,
            scope=_qualified_name(scope, node),
            detector="pattern",
            rule=rule["id"],
            confidence=confidence,
        )
        return [(call, (path, node.start_byte, node.end_byte))]
    return []


def _call_method(
    node: CallNode,
    positional: list[str],
    keyword: dict[str, str],
    rule: dict[str, Any],
    lookup: Lookup,
    patterns: Patterns,
) -> str | None:
    if rule.get("method_from_name"):
        return (node.name or "").upper() or None
    if "method_arg" in rule or "method_option" in rule:
        text = _argument(positional, keyword, rule, "method")
        value = evaluate_text(text, lookup, patterns) if text is not None else None
        if value and "{" not in value:
            return value.upper()
        if text is not None:  # present but dynamic
            return None
    method = rule.get("method")
    return str(method) if method else None


def _call_confidence(
    ctx: ApiMapContext,
    path: str,
    node: CallNode,
    url: str,
    scope: Scope,
    rule: dict[str, Any],
    patterns: Patterns,
) -> float | None:
    """Rule score plus textual evidence; ``None`` when nothing but the name speaks for an HTTP call."""

    if _non_http_receiver(scope, node, patterns):
        return None
    score, evidence = float(rule["confidence"]), bool(rule.get("name_is_evidence"))
    if patterns["absolute_url"].match(url):
        score, evidence = score + 0.15, True
    if node.subject and patterns["client_receiver"].search(node.subject):
        score, evidence = score + 0.1, True
    if scope["http_library"]:
        score, evidence = score + 0.1, True

    verdict = _scip_verdict(ctx, path, node, patterns)
    if verdict == "other":
        return None
    if verdict == "http":
        score, evidence = score + 0.2, True

    score = min(score, MAX_CALL_CONFIDENCE)
    if not evidence or score < patterns["min_call_confidence"]:
        return None
    return score


def _non_http_receiver(scope: Scope, node: CallNode, patterns: Patterns) -> bool:
    """``cache = {}`` / ``cache = new Map()`` then ``cache.get("/users/1")``: a container, not a client."""

    regex = patterns.get("non_http_receiver_init")
    if (
        regex is None
        or not node.subject
        or not re.fullmatch(r"[A-Za-z_$][\w$]*", node.subject)
    ):
        return False
    init = _scoped(scope, node, "inits")(node.subject)
    return init is not None and regex.match(init) is not None


def _scip_verdict(
    ctx: ApiMapContext, path: str, node: CallNode, patterns: Patterns
) -> str | None:
    """``"http"`` / ``"other"`` when SCIP knows the callee's owner, ``None`` when it does not.

    The callee span is found on bytes: the first occurrence of ``name`` after the subject.
    """

    if ctx.symbols is None or not node.name:
        return None
    raw = ctx.source(path)[node.start_byte : node.end_byte]
    name = node.name.encode("utf-8")
    offset = raw.find(name, len(node.subject.encode("utf-8")) if node.subject else 0)
    if offset < 0:
        return None
    start = node.start_byte + offset
    owner = ctx.scip_owner(path, start, start + len(name))
    if owner is None:
        return None
    if owner in patterns["http_owners"]:
        return "http"
    if owner.startswith(patterns["non_http_owner_prefixes"]):
        return "other"
    return None
