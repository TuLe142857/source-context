"""Application command-line interface."""

import typer

from .chunking import cli as chunk_command
from .parse_code import cli as parse_code_command


cli = typer.Typer()

cli.add_typer(
    parse_code_command,
)
cli.add_typer(
    chunk_command,
)


def run() -> None:
    """Run the root CLI application."""

    cli()


if __name__ == "__main__":
    run()
