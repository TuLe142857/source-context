import json
from pathlib import Path
from typing import Any, Literal

import typer

from app.parser.languages import get_language_registry
from app.parser.uast import UASTNode
from app.parser.exc import UnsupportedLanguageError
from app.util import TreeFormatter

cli = typer.Typer()


@cli.command("cst")
def parse_cst(
    file_path: str = typer.Argument("File path"),
    format_type: Literal["tree", "json"] = typer.Option("tree", "--format", "-fmt"),
) -> None:
    """Parse a source file into its concrete syntax tree.(Original output of tree-sitter)."""

    def cst_to_tree(node: Any) -> dict[str, list[Any]]:
        return {
            node.type: [cst_to_tree(child) for child in node.children],
        }

    def cst_to_dict(node: Any) -> dict[str, Any]:
        return {
            "type": node.type,
            "is_named": node.is_named,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "start_point": {
                "row": node.start_point[0],
                "column": node.start_point[1],
            },
            "end_point": {
                "row": node.end_point[0],
                "column": node.end_point[1],
            },
            "children": [cst_to_dict(child) for child in node.children],
        }

    source_path = Path(file_path)
    if (not source_path.exists()) or (not source_path.is_file()):
        raise ValueError("Invalid path")

    file_content_bytes = source_path.read_bytes()
    try:
        parser = get_language_registry().get_parser_for_file(source_path.name)
        cst = parser.parse(file_content_bytes)

        if format_type == "tree":
            print(TreeFormatter().format(cst_to_tree(cst.root_node)))
        else:
            print(json.dumps(cst_to_dict(cst.root_node), indent=2))
    except UnsupportedLanguageError as e:
        print(str(e))


@cli.command("uast")
def parse_uast(
    file_path: str = typer.Argument(),
    format_type: Literal["tree", "json"] = typer.Option("tree", "--format", "-fmt"),
) -> None:
    """
    Parse source file to UAST - Unified Abstract Syntax Tree(Converted from CST of tree-sitter).
    """

    def uast_to_dict(node: UASTNode) -> dict[str, Any]:
        node_type = node.node_type
        if hasattr(node, "kind"):
            node_type = getattr(node, "kind")
        key = f"[{node_type}] {node.name}"

        if node.docstring is not None:
            key += " (has doc)"
        if len(node.metadata) > 0:
            key += f" {node.metadata}"

        children = []
        for child in node.children:
            children.append(uast_to_dict(child))
        return {key: children}

    path = Path(file_path)
    if (not path.exists()) or (not path.is_file()):
        raise ValueError("Invalid path")

    filename = path.name
    file_content_bytes = path.read_bytes()

    language_registry = get_language_registry()

    try:
        parser = language_registry.get_parser_for_file(filename)
        converter = language_registry.get_converter_for_file(filename)
        ts_tree = parser.parse(file_content_bytes)
        uast_root = converter.convert(ts_tree, file_content_bytes)

        if format_type == "tree":
            uast_dict = uast_to_dict(uast_root)
            print(TreeFormatter().format(uast_dict))
        else:
            print(json.dumps(uast_root.to_dict(), indent=2))
    except UnsupportedLanguageError as e:
        print(str(e))
