import uuid

import typer
from neomodel import db

from app.graph.model import BranchNodeModel, RepositoryNodeModel

cli = typer.Typer(name="branch", help="Manage branches")


@cli.command("create", help="Create a new branch inside a repository")
def create_branch(
    branch_name: str = typer.Argument(help="Branch name"),
    repo_id: int = typer.Argument(help="Parent repository id"),
    commit_hash: str | None = typer.Option(
        None, "-c", "--commit-hash", help="Commit hash this branch points to"
    ),
) -> None:
    repo = RepositoryNodeModel.nodes.get_or_none(uid=repo_id)
    if repo is None:
        raise ValueError(f"Repository {repo_id} not found")

    branch = BranchNodeModel(
        uid=uuid.uuid4().int % 10**6,
        name=branch_name,
        commit_hash=commit_hash,
    )
    branch.save()
    repo.branches.connect(branch)
    print(f"Created new branch {branch.name} successfully. Id = {branch.uid}")


@cli.command("list", help="List branches")
def list_branches(
    repo_id: int | None = typer.Option(
        None, "-r", "--repo-id", help="Filter by parent repository id"
    ),
    name: str | None = typer.Option(
        None, "-n", "--name", help="Filter by branch name (substring, case-insensitive)"
    ),
) -> None:
    if repo_id is not None:
        repo = RepositoryNodeModel.nodes.get_or_none(uid=repo_id)
        if repo is None:
            raise ValueError(f"Repository {repo_id} not found")
        branches = (
            repo.branches.filter(name__icontains=name) if name else repo.branches.all()
        )
    else:
        branches = (
            BranchNodeModel.nodes.filter(name__icontains=name)
            if name
            else BranchNodeModel.nodes.all()
        )

    if not branches:
        print("No branch found")
        return

    print(f"{'ID':<25}{'NAME':<30}{'COMMIT HASH'}")
    for branch in branches:
        print(f"{branch.uid:<25}{branch.name:<30}{branch.commit_hash or ''}")


@cli.command("delete", help="Delete a branch")
def delete_branch(
    branch_id: int = typer.Argument(help="Branch id"),
    cascade: bool = typer.Option(
        False, "--cascade", help="Also delete every project and file under this branch"
    ),
) -> None:
    branch = BranchNodeModel.nodes.get_or_none(uid=branch_id)
    if branch is None:
        raise ValueError(f"Branch {branch_id} not found")

    if cascade:
        db.cypher_query(
            "MATCH (root:Branch {uid: $uid}) "
            "OPTIONAL MATCH (root)-[*]->(descendant) "
            "DETACH DELETE root, descendant",
            {"uid": branch_id},
        )
    else:
        branch.delete()

    print(f"Deleted branch {branch_id} successfully")
