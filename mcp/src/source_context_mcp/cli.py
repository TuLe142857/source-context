import typer

from .core.settings import CONFIG_FILE, get_settings, get_settings_with_overrides, write_settings
from .server import create_server

cli = typer.Typer()


@cli.command(name="run", help="Run the MCP server")
def run(
    server_url_override: str | None = typer.Option(
        None, "--server-url", help="Server url to override for this session"
    ),
    pat_override: str | None = typer.Option(None, "--token", help="Token to override for this session"),
    workspace_id: int | None = typer.Option(
        None, "--workspace-id", help="Default workspace id to override for this session"
    ),
):
    server = create_server(
        base_url_override=server_url_override,
        pat_override=pat_override,
        workspace_id_override=workspace_id,
    )
    server.run("stdio")


@cli.command(name="config", help="Configure the MCP server")
def config(
    server_url: str | None = typer.Option(None, "--server-url", help="Server URL"),
    token: str | None = typer.Option(None, "--token", help="Personal Access Token"),
    default_workspace_id: int | None = typer.Option(None, "--workspace-id", help="Default workspace id"),
):
    settings = get_settings_with_overrides(
        server_url_override=server_url,
        pat_override=token,
        default_workspace_id_override=default_workspace_id,
    )
    write_settings(settings)
    typer.echo(f"Config saved to {CONFIG_FILE}")


@cli.command(name="show-config", help="Show the MCP server's configuration")
def show_config():
    settings = get_settings()
    settings_json = settings.model_dump_json(indent=2)

    typer.echo(f"Configuration file: {CONFIG_FILE}")
    typer.echo("Note: Secret value will be display as ***")
    typer.echo(settings_json)
