import typer

from pathlib import Path
from neomodel import db
from app.parser.languages import get_language_registry
from app.graph.save_node import save_file_node
from app.graph.model import BranchNodeModel, ProjectNodeModel
from app.parser import UnsupportedLanguageError
from app.parser.uast import ContainerNode

import uuid

cli = typer.Typer(name="project", help="Manage projects")


@cli.command("create", help="Create a project and build its graph under a branch")
def create(
    p: str = typer.Argument(help="Project directory"),
    branch_id: int = typer.Argument(help="Parent branch id"),
    name: str | None = typer.Option(None, "-n", "--name", help="Project name"),
) -> None:
    root_dir = Path(p)

    if not (root_dir.exists()) or not (root_dir.is_dir()):
        raise ValueError(f"Project directory {root_dir} does not exist")
    if name is None:
        name = root_dir.name

    branch_node = BranchNodeModel.nodes.get_or_none(uid=branch_id)
    if branch_node is None:
        raise ValueError(f"Branch {branch_id} not found")

    files = [f for f in root_dir.rglob("*") if f.is_file()]

    # create project node
    project_node = ProjectNodeModel(
        uid=uuid.uuid4().int % 10**6,
        name=name,
        relative_path=str(root_dir),
    )
    project_node.save()
    project_node.branch.connect(branch_node)

    registry = get_language_registry()
    print(f"project name: {project_node.name}")
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
            file_node = save_file_node(uast_root, project_node.uid)

            project_node.files.connect(file_node)
        except UnsupportedLanguageError:
            continue

    print(f"Created project {project_node.name} successfully. Id = {project_node.uid}")


@cli.command("list", help="List projects")
def list_projects(
    branch_id: int | None = typer.Option(
        None, "-b", "--branch-id", help="Filter by parent branch id"
    ),
    name: str | None = typer.Option(
        None,
        "-n",
        "--name",
        help="Filter by project name (substring, case-insensitive)",
    ),
) -> None:
    if branch_id is not None:
        branch_node = BranchNodeModel.nodes.get_or_none(uid=branch_id)
        if branch_node is None:
            raise ValueError(f"Branch {branch_id} not found")

        query = "MATCH (:Branch {uid: $branch_id})-[:INCLUDES]->(p:Project) "
        params: dict = {"branch_id": branch_id}
        if name:
            query += "WHERE toLower(p.name) CONTAINS toLower($name) "
            params["name"] = name
        query += "RETURN p"

        results, _ = db.cypher_query(query, params)
        projects = [ProjectNodeModel.inflate(row[0]) for row in results]
    else:
        projects = (
            ProjectNodeModel.nodes.filter(name__icontains=name)
            if name
            else ProjectNodeModel.nodes.all()
        )

    if not projects:
        print("No project found")
        return

    print(f"{'ID':<45}{'NAME':<30}{'PATH'}")
    for project in projects:
        print(f"{project.uid:<45}{project.name:<30}{project.relative_path}")


@cli.command("delete", help="Delete a project")
def delete_project(
    project_id: str = typer.Argument(help="Project id"),
    cascade: bool = typer.Option(
        False, "--cascade", help="Also delete every file and node under this project"
    ),
) -> None:
    project = ProjectNodeModel.nodes.get_or_none(uid=project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    if cascade:
        db.cypher_query(
            "MATCH (root:Project {uid: $uid}) "
            "OPTIONAL MATCH (root)-[*]->(descendant) "
            "DETACH DELETE root, descendant",
            {"uid": project_id},
        )
    else:
        project.delete()

    print(f"Deleted project {project_id} successfully")
