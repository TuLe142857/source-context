"""NestJS endpoints - Hướng 2, provider side.

``@Get(":id")`` on a method of a ``@Controller("accounts")`` class, plus the global prefix of
``app.setGlobalPrefix("api")`` on the app ``NestFactory.create(...)`` returns. NestJS joins the
three as path segments: ``/api/accounts/:id``. Module wiring is not read: every controller of the
project is assumed served by its app.
"""

from __future__ import annotations

from typing import Any

from tree_sitter import Node

from app.engine.api_map.context import ApiMapContext
from app.engine.api_map.handlers.api_handler import Detection
from app.engine.api_map.handlers.rest_api_handler import RestApiHandler

from ..cst import (
    ObjectInfo,
    Site,
    arg,
    evaluate,
    object_property,
    resolve_object,
    scope_name,
    text,
)

VERB_DECORATORS = {
    "Get": "GET",
    "Post": "POST",
    "Put": "PUT",
    "Patch": "PATCH",
    "Delete": "DELETE",
    "Head": "HEAD",
    "Options": "OPTIONS",
    "All": "*",
}
COMMON = "@nestjs/common"
APP_KINDS = frozenset({"@nestjs/core.NestFactory.create()"})
METHOD_NAMES = frozenset({*VERB_DECORATORS, "setGlobalPrefix"})
CONFIDENCE = 0.9
"""Below FastAPI/Express: which module serves a controller is not checked."""


def visit(
    state: dict[str, Any], ctx: ApiMapContext, path: str, site: Site, obj: ObjectInfo
) -> None:
    method = text(site["method"])
    if method == "setGlobalPrefix":
        if obj[0] in APP_KINDS:
            prefix = evaluate(ctx, path, arg(site["args"], 0))
            if prefix is not None:
                state["global_prefix"] = prefix
        return
    if "handler" not in site or obj[0] != f"{COMMON}.{method}":
        return
    member: Node = site["handler"]
    controller = _controller_prefix(ctx, path, member)
    if controller is None:
        return  # a decorated method outside a controller
    route = arg(site["args"], 0)
    route = object_property(route, "path") or route
    local = evaluate(ctx, path, route) if route is not None else ""
    state.setdefault("routes", []).append(
        {
            "method": VERB_DECORATORS[method],
            "controller": controller,
            "path": local if local is not None else "{}",
            "raw": text(route) if route is not None else None,
            "file": path,
            "member": member,
            "decorator": method,
        }
    )


def finish(
    state: dict[str, Any], handler: RestApiHandler, ctx: ApiMapContext
) -> list[Detection]:
    global_prefix = state.get("global_prefix", "")
    detections: list[Detection] = []
    for route in state.get("routes", []):
        parts = [
            p.strip("/")
            for p in (global_prefix, route["controller"], route["path"])
            if p.strip("/")
        ]
        member: Node = route["member"]
        node = handler.endpoint_node(
            ctx,
            method=route["method"],
            path="/" + "/".join(parts),
            framework="nestjs",
            raw=route["raw"],
            file=route["file"],
            handler_name=scope_name(member),
            detector="framework",
            rule=f"nestjs.{route['decorator']}",
            confidence=CONFIDENCE,
            controller=route["controller"],
            global_prefix=global_prefix,
            local_path=route["path"],
        )
        detections.append((node, (route["file"], member.start_byte, member.end_byte)))
    return detections


def _controller_prefix(ctx: ApiMapContext, path: str, member: Node) -> str | None:
    """Path of the ``@Controller`` decorating the class of ``member``; ``None`` without one."""

    cls: Node | None = member.parent
    while cls is not None and cls.type not in (
        "class_declaration",
        "abstract_class_declaration",
        "class",
    ):
        cls = cls.parent
    if cls is None:
        return None
    decorators = [c for c in cls.children if c.type == "decorator"]
    if cls.parent is not None and cls.parent.type == "export_statement":
        decorators += [c for c in cls.parent.children if c.type == "decorator"]
    for decorator in decorators:
        call = decorator.named_children[0] if decorator.named_children else None
        if call is None or call.type != "call_expression":
            continue
        function = call.child_by_field_name("function")
        kind, _, _ = resolve_object(ctx, path, function)
        if kind != f"{COMMON}.Controller":
            continue
        value = arg(call.child_by_field_name("arguments"), 0)
        value = object_property(value, "path") or value
        return (evaluate(ctx, path, value) or "") if value is not None else ""
    return None
