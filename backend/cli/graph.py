import typer
from pathlib import Path
import subprocess
import tree_sitter

cli = typer.Typer(name="graph")


def build_tree_sitter(p: Path) -> tree_sitter.Tree:
    pass


@cli.command(name="build")
def build_graph(
    directory: str = typer.Argument(
        help="project directory.Currently support python only"
    ),
):
    root_dir = Path(directory)
    if not (root_dir.exists()) or not (root_dir.is_dir()):
        raise ValueError("Invalid directory")
    print(root_dir.absolute())

    for path in root_dir.rglob("**/*.py"):
        print(path.relative_to(root_dir))

    # build tree
    # lang_registry = get_language_registry()
    # parser = lang_registry.get_parser("python")
    # converter = lang_registry.get_parser("python")

    # index with scip
    scip_out = Path("cli_index.scip")

    subprocess.run(
        [
            "scip-python",
            "index",
            f"{root_dir.absolute()}",
            "--output",
            scip_out.absolute(),
        ]
    )

    scip_out_json = scip_out.parent / "cli_index.json"
    res_json = subprocess.run(
        [
            "/home/tule/go/bin/scip",
            "print",
            scip_out.absolute(),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    import json

    formated_json = json.dumps(json.loads(res_json.stdout), indent=2)
    scip_out_json.write_text(formated_json)
    # buil
    # d graph
