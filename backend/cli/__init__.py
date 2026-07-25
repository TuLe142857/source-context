import typer

from .parse_code import cli as parse_code_command
from .chunking import cli as chunk_command
from .scip import cli as scip_command
from .graph import cli as graph_command

cli = typer.Typer()


cli.add_typer(parse_code_command)
cli.add_typer(chunk_command)
cli.add_typer(graph_command)
cli.add_typer(scip_command)


def run() -> None:
    cli()


if __name__ == "__main__":
    run()
