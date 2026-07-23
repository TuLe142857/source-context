"""CLI entry point for source-context-mcp."""

import typer

from .config import load_config, set_api_key
from .server import mcp

app = typer.Typer(
    name="source-context-mcp",
    help="Source Context MCP Server & CLI Application.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Default action: Run the FastMCP server via stdio when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        mcp.run()


@app.command(name="run")
def run_server() -> None:
    """Run the MCP server stdio service."""
    mcp.run()


@app.command(name="setup")
def setup_cmd(
    api_key: str = typer.Option(..., "--api-key", "-k", help="API Key / PAT cấp từ FastAPI backend"),
    server_url: str | None = typer.Option(
        None,
        "--server-url",
        "-u",
        help="URL địa chỉ FastAPI backend (vd: http://localhost:8000/api/v1)",
    ),
) -> None:
    """Configure API Key and backend URL for the MCP server."""
    set_api_key(api_key, server_url)
    cfg = load_config()
    typer.echo("[OK] Cau hinh da duoc luu thanh cong!")
    typer.echo(f"  Server URL: {cfg.server_url}")
    if cfg.api_key:
        typer.echo(f"  API Key: {cfg.api_key[:10]}...")


def main() -> None:
    """Main CLI execution entry point."""
    app()


if __name__ == "__main__":
    main()
