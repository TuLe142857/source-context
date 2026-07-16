import typer

from .parse_code import cli as parse_code_command

cli = typer.Typer()

cli.add_typer(parse_code_command)


def run() -> None:
    cli()


if __name__ == "__main__":
    run()
