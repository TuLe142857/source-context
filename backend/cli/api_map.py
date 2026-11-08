import json
from pathlib import Path

import typer
from tabulate import tabulate  # type: ignore[import-untyped]

from app.engine.api_map.handlers.api_handler import api_metadata
from app.engine.api_map import (
    ApiMapContext,
    build_api_map_for_project,
    detect_apis,
    link_api_map,
)
from app.engine.parser import UnsupportedLanguageError
from app.engine.parser.languages import get_language_registry
from app.engine.scip import scip_pb2
from app.engine.scip.index_reader import read_index

cli = typer.Typer(
    name="api-map", help="Detect API endpoints and calls, link calls to endpoints"
)

_SKIPPED_PARTS = ("node_modules", "__pycache__", "venv", ".venv")


def _read_index(path: str | None) -> scip_pb2.Index | None:
    if path is None:
        return None
    index = scip_pb2.Index()
    index.ParseFromString(Path(path).read_bytes())
    return index


def _source_files(root: Path) -> list[str]:
    """Files the indexing pipeline would parse, relative to ``root``."""

    registry = get_language_registry()
    files = []
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root)
        if not file.is_file() or any(
            p.startswith(".") or p in _SKIPPED_PARTS for p in relative.parts
        ):
            continue
        try:
            registry.resolve_language_name(file.name)
        except UnsupportedLanguageError:
            continue
        files.append(relative.as_posix())
    return files


@cli.command("detect", help="Print the APIs of a directory, without Neo4j")
def detect(
    project_dir: str = typer.Argument(help="Project directory"),
    scip: str | None = typer.Option(
        None, "--scip", help="SCIP index of the project (index.scip)"
    ),
    as_json: bool = typer.Option(False, "--json", help="One JSON object per API"),
) -> None:
    root = Path(project_dir).resolve()
    index = _read_index(scip)
    files = {path: path for path in _source_files(root)}
    ctx = ApiMapContext(
        0, root, files, read_index(index) if index is not None else None
    )
    detections = sorted(
        detect_apis(ctx), key=lambda d: (type(d[0]).__name__, d[0].signature or "")
    )

    if as_json:
        for node, anchor in detections:
            print(
                json.dumps(
                    {
                        "type": type(node).__name__,
                        **node.__properties__,
                        "anchor": anchor,
                    },
                    default=str,
                )
            )
        return
    rows = [
        [
            "endpoint" if "Endpoint" in type(node).__name__ else "call",
            node.signature,
            node.match_key,
            getattr(node, "target_hint", None)
            or getattr(node, "framework", None)
            or "",
            f"{api_metadata(node)['detector']}:{api_metadata(node)['rule']}",
            api_metadata(node)["confidence"],
            f"{anchor[0]}:{anchor[1]}" if anchor else "",
        ]
        for node, anchor in detections
    ]
    print(
        tabulate(
            rows,
            headers=[
                "role",
                "signature",
                "match_key",
                "host/framework",
                "rule",
                "conf",
                "anchor",
            ],
        )
    )


@cli.command("build", help="Detect and store the APIs of a project already in Neo4j")
def build(
    project_id: int = typer.Argument(help="Project uid in Neo4j"),
    project_dir: str = typer.Argument(
        help="Project directory the File paths are relative to"
    ),
    scip: str | None = typer.Option(None, "--scip", help="SCIP index of the project"),
) -> None:
    summary = build_api_map_for_project(
        project_id, Path(project_dir).resolve(), index=_read_index(scip)
    )
    print(summary)


@cli.command("link", help="Link API calls to endpoints across projects (one workspace)")
def link(
    project_ids: list[int] = typer.Argument(help="Project uids of the workspace"),
    include_tests: bool = typer.Option(
        False, "--include-tests", help="Also link calls made in tests"
    ),
) -> None:
    print(f"{link_api_map(project_ids, include_tests=include_tests)} links")
