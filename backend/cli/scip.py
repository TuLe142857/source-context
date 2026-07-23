from app.scip import scip_pb2

import typer

from pathlib import Path

cli = typer.Typer(name="scip")


@cli.command(name="inspect", help="Inspect scip output(file)")
def inspect(file_path: str = typer.Argument(help="File path")):
    path = Path(file_path)
    if (not path.exists()) or (not path.is_file()):
        raise ValueError("Path is not exists or not a file")

    content_bytes = path.read_bytes()

    index = scip_pb2.Index()
    index.ParseFromString(content_bytes)
    print("Metadata")
    print(index.metadata)

    print(f"{len(index.documents)} documents:")
    for doc in index.documents:
        print("path:", doc.relative_path)
        print(f"symbol: {len(doc.symbols)}")
        print(f"occurrences: {len(doc.occurrences)}")
        print("----")

    print(index)
