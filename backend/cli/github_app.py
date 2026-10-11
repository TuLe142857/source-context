import typer

import httpx
import time
import jwt
import json
from pathlib import Path
import base64
from typing import Annotated

cli = typer.Typer()

class GitHubApp:
    """
    https://docs.github.com/en/rest?apiVersion=2026-03-10
    """
    API_VERSION = "2026-03-10"
    def __init__(self, app_id: str, app_name:str, private_key: str):
        self.app_id = app_id
        self.app_name = app_name
        self.private_key = private_key
        self.client = httpx.Client(base_url="https://api.github.com")



    def _create_jwt(self) -> str:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": self.app_id}
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _app_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._create_jwt()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }

    def _token_headers(self,  token: str, raw: bool = False) -> dict:
        accept = "application/vnd.github.raw+json" if raw else "application/vnd.github+json"
        return {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": self.API_VERSION,
        }

    # ---------- App-level APIs ----------

    def install_url(self) -> str:
        return f"https://github.com/apps/{self.app_name}/installations/new"

    def list_installations(self) -> list[dict]:
        r = self.client.get("/app/installations", headers=self._app_headers())
        r.raise_for_status()
        return r.json()

    # ---------- Installation-level APIs ----------

    def get_installation_token(self, installation_id: int) -> str:
        r = self.client.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers=self._app_headers(),
            json={"permissions": {"contents": "read"}},  # ép token chỉ có quyền đọc
        )
        r.raise_for_status()
        return r.json()["token"]

    def list_repos(self, token: str) -> list:
        r = self.client.get(
            "/installation/repositories",
            headers=self._token_headers(token),
            params={"per_page": 100},
        )
        r.raise_for_status()
        return r.json()["repositories"]

    def get_content(self, token: str, full_name: str, path: str = "") -> list | dict:
        r = self.client.get(
            f"/repos/{full_name}/contents/{path}",
            headers=self._token_headers(token),
        )
        r.raise_for_status()
        return r.json()

    def list_files(self, token: str, full_name: str, path: str = "") -> list[dict]:
        r = self.client.get(
            f"/repos/{full_name}/contents/{path}",
            headers=self._token_headers(token),
        )
        r.raise_for_status()
        return [{"path": i["path"], "type": i["type"]} for i in r.json()]

    def read_file(self, token: str, full_name: str, path: str) -> str:
        r = self.client.get(
            f"/repos/{full_name}/contents/{path}",
            headers=self._token_headers(token, raw=True),
        )
        r.raise_for_status()
        return r.text


GITHUB_APP_NAME = "source-context-dev"
GITHUB_APP_ID = "4708904"
GITHUB_APP_PRIVATE_KEY = base64.b64decode((Path(__file__).parent / "key_base64.txt").read_text()).decode()

github_app = GitHubApp(
    app_name = GITHUB_APP_NAME,
    app_id = GITHUB_APP_ID,
    private_key = GITHUB_APP_PRIVATE_KEY,
)

@cli.command(name="install_url", help="Show installation url for GitHub App")
def get_installation_url() -> None:
    typer.echo(github_app.install_url())

@cli.command(name="installations", help="List users that installed the app.")
def list_installations(
        raw: Annotated[bool, typer.Option(help="Show raw API response")] = False,
) -> None:
    installations = github_app.list_installations()
    for installation in installations:
        if raw:
            typer.echo(json.dumps(installation, indent=2))
        else:
            typer.echo(json.dumps(
                {
                    "id": installation["id"],
                    "username": installation["account"]["login"],
                    "repository_selection": installation["repository_selection"],
                }, indent=2))


@cli.command(name="repos", help="List repositories the installation can access.")
def list_repos(
    installation_id: Annotated[int, typer.Argument(help="Installations ID")],
    raw: Annotated[bool, typer.Option(help="Show raw API response")] = False,
) -> None:
    token = github_app.get_installation_token(installation_id)
    repos = github_app.list_repos(token)
    for repo in repos:
        if raw:
            typer.echo(json.dumps(repo, indent=2))
        else:
            typer.echo(json.dumps(
                {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "private": repo["private"],
                }, indent=2))

@cli.command(name="files", help="List files and folders in a repository path.")
def list_files(
    installation_id: Annotated[int, typer.Argument(help="Installation ID (see `installations`).")],
    repo: Annotated[str, typer.Argument(help="Repository full name, format: <owner>/<repo>.")],
    path: Annotated[str, typer.Argument(help="Path from the repository root (default: root).")] = "",
) -> None:
    token = github_app.get_installation_token(installation_id)
    files = github_app.list_files(token, repo, path)

    typer.echo(json.dumps(files, indent=2))



@cli.command(name="read", help = "Read file content of repo")
def read_file(
    installation_id: int = typer.Argument(..., help="Installation ID"),
    repo: str = typer.Argument(..., help="Repository full name, format: <owner>/<repo>."),
    path: str = typer.Argument(..., help="File path, e.g. README.md."),
) -> None:
    token = github_app.get_installation_token(installation_id)
    content = github_app.read_file(token, repo, path)
    typer.echo(content)