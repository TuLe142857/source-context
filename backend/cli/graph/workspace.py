import uuid

import typer
from neomodel import db

from app.graph.model import WorkspaceNodeModel

cli = typer.Typer(name="workspace", help="Manage workspaces")


@cli.command("add", help="Create a new workspace")
def add_new_workspace(
    workspace_name: str = typer.Argument(help="Workspace name"),
) -> None:
    workspace = WorkspaceNodeModel(
        uid=uuid.uuid4().int % 10**6,
        name=workspace_name,
    )
    workspace.save()
    print(f"Created new workspace {workspace.name} successfully. Id = {workspace.uid}")


@cli.command("list", help="List workspaces")
def list_workspaces(
    name: str | None = typer.Option(
        None,
        "-n",
        "--name",
        help="Filter by workspace name (substring, case-insensitive)",
    ),
) -> None:
    workspaces = (
        WorkspaceNodeModel.nodes.filter(name__icontains=name)
        if name
        else WorkspaceNodeModel.nodes.all()
    )

    if not workspaces:
        print("No workspace found")
        return

    print(f"{'ID':<25}{'NAME'}")
    for workspace in workspaces:
        print(f"{workspace.uid:<25}{workspace.name}")


@cli.command("delete", help="Delete a workspace")
def delete_workspace(
    workspace_id: int = typer.Argument(help="Workspace id"),
    cascade: bool = typer.Option(
        False,
        "--cascade",
        help="Also delete every repository, branch, project and file under this workspace",
    ),
) -> None:
    workspace = WorkspaceNodeModel.nodes.get_or_none(uid=workspace_id)
    if workspace is None:
        raise ValueError(f"Workspace {workspace_id} not found")

    if cascade:
        db.cypher_query(
            "MATCH (root:Workspace {uid: $uid}) "
            "OPTIONAL MATCH (root)-[*]->(descendant) "
            "DETACH DELETE root, descendant",
            {"uid": workspace_id},
        )
    else:
        workspace.delete()

    print(f"Deleted workspace {workspace_id} successfully")
