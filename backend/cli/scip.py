import typer

import docker
from pathlib import Path

from docker.types import Mount

from app.scip import scip_pb2

cli = typer.Typer(name="scip", help="SCIP Code Intelligence Protocol")


@cli.command("index", help="Index project. Currently, only python is supported")
def index_project(
    p: str = typer.Argument(),
    out_path: str = typer.Option(
        "index.scip", "--out-file", help="Output file name. Default is index.scip"
    ),
):
    # Dùng resolve() thay vì absolute()
    project_root = Path(p).resolve()
    project_name = project_root.name

    if not (project_root.exists()) or not (project_root.is_dir()):
        raise ValueError("Invalid project path")

    out_file_path = Path(out_path).resolve()
    if out_file_path.is_dir():
        out_dir_path = out_file_path
        out_file_path = out_dir_path / "index.scip"
    else:
        out_dir_path = out_file_path.parent.resolve()

    mounts = [
        Mount(
            target=f"/sandbox/project/{project_name}",
            source=str(project_root),
            type="bind",
            read_only=False,
        ),
        Mount(
            target="/sandbox/output",
            source=str(out_dir_path),
            type="bind",
            read_only=False,
        ),
    ]

    docker_client = docker.from_env()
    docker_client.containers.run(
        image="sandbox/python313:latest",
        command=f"scip-python index --output /sandbox/output/{out_file_path.name}",
        mounts=mounts,
        working_dir=f"/sandbox/project/{project_name}",
        remove=True,
    )


@cli.command("inspect")
def inspect_scip_project(
    p: str = typer.Argument(),
):
    file = Path(p)
    if not (file.exists()) or not (file.is_file()):
        raise ValueError("Invalid file path")

    index = scip_pb2.Index()
    index.ParseFromString(file.read_bytes())
    print(f"document count: {len(index.documents)}")
    for doc in index.documents:
        print(doc.relative_path)
