import sys

import typer

from .parse_code import cli as parse_code_command

cli = typer.Typer()


@cli.command("greet")
def greeting():
    if sys.stdin.isatty():
        typer.echo("Vui lòng nhập văn bản (Nhấn Ctrl+D trên Linux/Mac hoặc Ctrl+Z trên Windows để kết thúc):")

    content = sys.stdin.read()
    print(content)


cli.add_typer(parse_code_command)


def run() -> None:
    cli()


if __name__ == "__main__":
    run()
