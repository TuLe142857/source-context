import typer

from .workspace import cli as workspace_command
from .repo import cli as repo_command
from .branch import cli as branch_command
from .project import cli as project_command

cli = typer.Typer(
    name="graph",
    help="Manage the code graph: workspaces, repositories, branches and projects",
)

cli.add_typer(workspace_command)
cli.add_typer(repo_command)
cli.add_typer(branch_command)
cli.add_typer(project_command)
