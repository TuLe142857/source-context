import typer

from .parse_code import cli as parse_code_command
from .scip import cli as scip_command
from .graph import cli as graph_command

cli = typer.Typer()


cli.add_typer(parse_code_command, name="parse", help="Parse source code to tree.")
cli.add_typer(scip_command)
cli.add_typer(graph_command)


def run() -> None:
    cli()


if __name__ == "__main__":
    run()
