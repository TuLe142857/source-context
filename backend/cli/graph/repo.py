import uuid

import typer
from neomodel import db

from app.graph.model import RepositoryNodeModel, WorkspaceNodeModel

cli = typer.Typer(name="repo", help="Manage repositories")


@cli.command("create", help="Create a new repository inside a workspace")
def create_repo(
    workspace_id: int = typer.Argument(help="Parent workspace id"),
    repo_name: str = typer.Argument(help="Repository name"),
) -> None:
    workspace = WorkspaceNodeModel.nodes.get_or_none(uid=workspace_id)
    if workspace is None:
        raise ValueError(f"Workspace {workspace_id} not found")

    repo = RepositoryNodeModel(
        uid=uuid.uuid4().int % 10**6,
        name=repo_name,
    )
    repo.save()
    workspace.repositories.connect(repo)
    print(f"Created new repository {repo.name} successfully. Id = {repo.uid}")


@cli.command("list", help="List repositories")
def list_repos(
    workspace_id: int | None = typer.Option(
        None, "-w", "--workspace-id", help="Filter by parent workspace id"
    ),
    name: str | None = typer.Option(
        None,
        "-n",
        "--name",
        help="Filter by repository name (substring, case-insensitive)",
    ),
) -> None:
    if workspace_id is not None:
        workspace = WorkspaceNodeModel.nodes.get_or_none(uid=workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace {workspace_id} not found")
        repos = (
            workspace.repositories.filter(name__icontains=name)
            if name
            else workspace.repositories.all()
        )
    else:
        repos = (
            RepositoryNodeModel.nodes.filter(name__icontains=name)
            if name
            else RepositoryNodeModel.nodes.all()
        )

    if not repos:
        print("No repository found")
        return

    print(f"{'ID':<25}{'NAME'}")
    for repo in repos:
        print(f"{repo.uid:<25}{repo.name}")


@cli.command("delete", help="Delete a repository")
def delete_repo(
    repo_id: int = typer.Argument(help="Repository id"),
) -> None:
    repo = RepositoryNodeModel.nodes.get_or_none(uid=repo_id)
    if repo is None:
        raise ValueError(f"Repository {repo_id} not found")

    db.cypher_query(
        "MATCH (root:Repository {uid: $uid}) "
        "OPTIONAL MATCH (root)-[*]->(descendant) "
        "DETACH DELETE root, descendant",
        {"uid": repo_id},
    )

    print(f"Deleted repository {repo_id} successfully")
