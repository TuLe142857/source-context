import typer
from pathlib import Path

from app.scip import scip_pb2
from app.scip.sandbox import get_scip_sandbox_registry

cli = typer.Typer(name="scip", help="SCIP Code Intelligence Protocol")


@cli.command("ls", help="List all available language sandboxes")
def list_sandbox() -> None:
    registry = get_scip_sandbox_registry()
    print("success")
    for lang in registry.get_available_language():
        print(lang)
        sandbox = registry.get_sandbox(lang)
        if sandbox:
            print(f"Supported sandbox: {sandbox.image_tags}")


@cli.command("index", help="Index project. Currently, only python is supported")
def index_project(
    p: str = typer.Argument(),
    language: str = typer.Option("python", "--language"),
    out_path: str = typer.Option(
        "index.scip", "--out-file", help="Output file name. Default is index.scip"
    ),
) -> None:
    registry = get_scip_sandbox_registry()
    sandbox = registry.get_sandbox(language)
    if sandbox is None:
        raise ValueError(f"No SCIP sandbox found for language: {language}")
    result_bytes = sandbox.index(p)
    out_file_path = Path(out_path)
    out_file_path.write_bytes(result_bytes)


@cli.command("inspect")
def inspect_scip_project(
    p: str = typer.Argument(),
) -> None:
    file = Path(p)
    if not (file.exists()) or not (file.is_file()):
        raise ValueError("Invalid file path")

    index = scip_pb2.Index()
    index.ParseFromString(file.read_bytes())
    print(f"document count: {len(index.documents)}")
    for doc in index.documents:
        print(doc.relative_path)
