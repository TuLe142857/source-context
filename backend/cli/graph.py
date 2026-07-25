import typer

from pathlib import Path
from app.parser.languages import get_language_registry
from app.graph.build_graph import build_graph_for_file
from app.graph.model import ProjectNodeModel
from app.parser import UnsupportedLanguageError
from app.parser.uast import ContainerNode

import uuid

cli = typer.Typer(name="graph")


@cli.command("build", help="Build graph for project")
def build(
    p: str = typer.Argument(help="Project directory"),
    name: str | None = typer.Option(None, "-n", "--name", help="Project name"),
) -> None:
    root_dir = Path(p)

    if not (root_dir.exists()) or not (root_dir.is_dir()):
        raise ValueError(f"Project directory {root_dir} does not exist")
    if name is None:
        name = root_dir.name

    files = [f for f in root_dir.rglob("*") if f.is_file()]

    project_node = ProjectNodeModel(
        uid=str(uuid.uuid4()),
        name=name,
        relative_path=str(root_dir),
    )
    project_node.save()

    registry = get_language_registry()

    for file in files:
        try:
            content_bytes = file.read_bytes()
            ts_tree = registry.get_parser_for_file(file.name).parse(content_bytes)
            uast_root = registry.get_converter_for_file(file.name).convert(
                ts_tree, content_bytes, str(file)
            )
            if not isinstance(uast_root, ContainerNode):
                continue
            print(f"Build graph for {file.name}")
            file_node = build_graph_for_file(uast_root)

            project_node.files.connect(file_node)
        except UnsupportedLanguageError:
            continue
