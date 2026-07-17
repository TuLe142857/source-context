from pathlib import Path
from typing import Any

import typer

from app.languages import get_language_registry
from app.parser import FunctionNode, UASTNode
from app.util import TreeFormatter

cli = typer.Typer()


def uast_to_dict(node: UASTNode) -> dict[str, Any]:
    # Format expected by TreeFormatter: {"NodeLabel": [children_dicts]}
    key = f"[{node.node_type}] {node.name}"

    if node.docstring is not None:
        key += " (has doc)"
    if len(node.metadata) > 0:
        key += f" {node.metadata}"

    if isinstance(node, FunctionNode):
        key += f" {node.kind}"
    children = []
    for child in node.children:
        children.append(uast_to_dict(child))
    return {key: children}


@cli.command("parse")
def parse_code(path: str = typer.Argument()) -> None:
    path = Path(path)
    if (not path.exists()) or (not path.is_file()):
        raise ValueError("Invalid path")

    filename = path.name
    file_content_bytes = path.read_bytes()

    language_registry = get_language_registry()

    language_name = language_registry.resolve_language_name(filename)
    parser = language_registry.get_parser(language_name)
    converter = language_registry.get_converter(language_name)

    ts_tree = parser.parse(file_content_bytes)
    uast_root = converter.convert(ts_tree, file_content_bytes)
    print(type(converter))
    print(type(uast_root))
    # return
    uast_dict = uast_to_dict(uast_root)
    print(TreeFormatter().format(uast_dict))
