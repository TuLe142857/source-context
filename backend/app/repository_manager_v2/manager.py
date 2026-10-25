"""Repository Manager V2 with GitHub App private repository support.

This module provides services and utilities to authenticate via GitHub App installation tokens,
inspect authorized repositories, fetch branch metadata, clone or download private/public repositories,
and execute post-download processing hooks.
"""

from collections.abc import Sequence
from datetime import datetime
import logging
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any
from urllib.parse import urlparse

import jwt
import requests

from app.core.config import Settings, settings
from app.domain.repository import GitRepositoryMetadata
from app.repository_manager_v2.exceptions import (
    GitCommandError,
    GitCommandTimeoutError,
    GitExecutableNotFoundError,
    GitHubAppApiError,
    GitHubAppAuthenticationError,
)
from app.repository_manager_v2.profile_extractor.models import RepoProfileResult
from app.repository_manager_v2.profile_extractor.service import RepoProfileService

logger = logging.getLogger(__name__)


# ==============================================================================
# HOOK XỬ LÝ SAU KHI TẢI REPO (DELEGATES TO PROFILE_EXTRACTOR SERVICE)
# ==============================================================================
def post_download_metadata_hook(
    destination: Path,
    repository_url: str | None = None,
    branch_name: str | None = None,
    commit_sha: str | None = None,
    extra_info: dict[str, Any] | None = None,
    subprojects: list[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """Hook xử lý sau khi clone hoặc tải repository về hoàn tất.

    Delegates to RepoProfileService to extract repository metadata and subprojects.

    Args:
        destination (Path): Đường dẫn thư mục cục bộ chứa mã nguồn repository.
        repository_url (str | None, optional): Git clone URL của repository. Defaults to None.
        branch_name (str | None, optional): Tên branch vừa tải về. Defaults to None.
        commit_sha (str | None, optional): Commit hash hiện tại. Defaults to None.
        extra_info (dict[str, Any] | None, optional): Thông tin phụ thêm nếu có. Defaults to None.
        subprojects (list[tuple[str, str, str]] | None, optional): Danh sách (name, root_dir, language).

    Returns:
        dict[str, Any]: Dữ liệu thông tin cơ bản và profile được bóc tách từ repository.
    """
    profiler = RepoProfileService()
    profile = profiler.profile_repository(
        destination=destination,
        repository_url=repository_url,
        branch_name=branch_name or "main",
        commit_sha=commit_sha or "HEAD",
        subprojects=subprojects,
    )

    metadata: dict[str, Any] = {
        "repository_url": profile.repository_url,
        "branch_name": profile.branch_name,
        "commit_sha": profile.commit_sha,
        "local_path": str(destination),
        "primary_language": profile.primary_language,
        "summary": profile.summary,
        "readme_content": profile.readme_content,
        "license_name": profile.license_name,
        "topics": profile.topics,
        "languages_breakdown": profile.languages_breakdown,
        "subrepos": [s.model_dump() for s in profile.subrepos],
        "extra_info": profile.extra_info,
    }

    logger.info(
        "post_download_metadata_hook hoàn thành cho %s: %d subrepos, language=%s",
        destination.name,
        len(profile.subrepos),
        profile.primary_language,
    )
    return metadata


class RepoManagerV2:
    """Repository service orchestrator supporting GitHub App authentication and private repos."""

    def __init__(
        self,
        app_settings: Settings | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        """Initialize the RepoManagerV2 service.

        Args:
            app_settings (Settings | None, optional): Application settings. Defaults to None.
            timeout_seconds (int, optional): Timeout in seconds for Git operations. Defaults to 120.
        """
        self._settings = app_settings or settings
        self._timeout_seconds = timeout_seconds
        self._token_cache: dict[int, tuple[str, float]] = {}
        self._cache_lock = threading.Lock()

    def get_private_key(self) -> str:
        """Resolve and read the GitHub App RSA private key.

        Returns:
            str: PEM formatted private key string.

        Raises:
            GitHubAppAuthenticationError: If the private key cannot be located or read.
        """
        # 1. Check raw private key in settings
        raw_key = self._settings.GITHUB_APP_PRIVATE_KEY.get_secret_value().strip()
        if raw_key:
            return raw_key.replace("\\n", "\n")

        # 2. Check specified private key path in settings
        if self._settings.GITHUB_APP_PRIVATE_KEY_PATH is not None:
            key_path = Path(self._settings.GITHUB_APP_PRIVATE_KEY_PATH).expanduser()
            if not key_path.is_absolute():
                # Check relative to project root or cwd
                root_dir = Path(__file__).resolve().parents[3]
                backend_dir = Path(__file__).resolve().parents[2]
                potential_paths = [
                    key_path,
                    root_dir / key_path,
                    backend_dir / key_path,
                    Path("/app") / key_path,
                    Path("/app/backend") / key_path,
                    Path.cwd() / key_path,
                    Path.cwd().parent / key_path,
                ]
                for p in potential_paths:
                    if p.is_file():
                        try:
                            return p.read_text(encoding="utf-8").strip()
                        except OSError as exc:
                            raise GitHubAppAuthenticationError(
                                f"Failed to read private key at {p}: {exc}"
                            ) from exc
            elif key_path.is_file():
                try:
                    return key_path.read_text(encoding="utf-8").strip()
                except OSError as exc:
                    raise GitHubAppAuthenticationError(
                        f"Failed to read private key at {key_path}: {exc}"
                    ) from exc

        # 3. Fallback: Search for *.private-key.pem or *.pem in root and parent directories
        search_dirs = [
            Path(__file__).resolve().parents[3],
            Path(__file__).resolve().parents[2],
            Path("/app"),
            Path("/app/backend"),
            Path.cwd(),
            Path.cwd().parent,
        ]
        for sdir in search_dirs:
            if sdir.is_dir():
                pem_files = (
                    list(sdir.glob("*.private-key.pem"))
                    + list(sdir.glob("*source-context*.pem"))
                    + list(sdir.glob("*.pem"))
                )
                if pem_files:
                    try:
                        return pem_files[0].read_text(encoding="utf-8").strip()
                    except OSError as exc:
                        raise GitHubAppAuthenticationError(
                            f"Failed to read discovered PEM file {pem_files[0]}: {exc}"
                        ) from exc

        raise GitHubAppAuthenticationError(
            "GitHub App private key (.pem) not found. Please provide SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY "
            "or set SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY_PATH."
        )

    def create_app_jwt(self, expiration_seconds: int = 600) -> str:
        """Create a temporary JWT signed by the GitHub App private key.

        Args:
            expiration_seconds (int, optional): Expiration time in seconds (max 600s / 10m). Defaults to 600.

        Returns:
            str: Signed JWT string.

        Raises:
            GitHubAppAuthenticationError: If token signing fails.
        """
        app_id = str(self._settings.GITHUB_APP_ID).strip()
        if not app_id:
            raise GitHubAppAuthenticationError("GitHub App ID is not configured.")

        private_key = self.get_private_key()
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + min(expiration_seconds, 600),
            "iss": app_id,
        }

        try:
            return jwt.encode(payload, private_key, algorithm="RS256")
        except jwt.PyJWTError as exc:
            raise GitHubAppAuthenticationError(
                f"Failed to sign JWT with GitHub App private key: {exc}"
            ) from exc

    def get_installation_token(self, installation_id: int) -> str:
        """Generate or retrieve a cached Installation Access Token for the given installation.

        Tokens are valid for 1 hour; this method caches valid tokens in memory
        with a safety buffer to avoid unnecessary GitHub API requests.

        Args:
            installation_id (int): The GitHub App installation ID.

        Returns:
            str: The installation access token (starts with ghs_...).

        Raises:
            GitHubAppAuthenticationError: If token generation fails.
        """
        now = time.time()
        with self._cache_lock:
            cached = self._token_cache.get(installation_id)
            if cached is not None:
                token, expires_at = cached
                if expires_at > now + 120:  # 2 minute buffer
                    return token

        jwt_token = self.create_app_jwt()
        url = (
            f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        )
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }

        try:
            response = requests.post(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            token = str(data["token"])

            # Compute expiry
            expires_at_str = data.get("expires_at")
            if expires_at_str:
                try:
                    exp_dt = datetime.fromisoformat(
                        expires_at_str.replace("Z", "+00:00")
                    )
                    expires_at_ts = exp_dt.timestamp()
                except ValueError:
                    expires_at_ts = now + 3500
            else:
                expires_at_ts = now + 3500

            with self._cache_lock:
                self._token_cache[installation_id] = (token, expires_at_ts)

            return token
        except requests.RequestException as exc:
            logger.error(
                "Error minting installation token for installation %d: %s",
                installation_id,
                exc,
            )
            raise GitHubAppAuthenticationError(
                f"Failed to acquire installation token from GitHub: {exc}"
            ) from exc

    def list_authorized_repos(
        self, token_or_installation_id: str | int
    ) -> list[dict[str, Any]]:
        """List all repositories authorized for the installation.

        Args:
            token_or_installation_id (str | int): Installation access token or installation ID.

        Returns:
            list[dict[str, Any]]: List of repository data dictionaries.

        Raises:
            GitHubAppApiError: If the GitHub API returns an error.
        """
        if isinstance(token_or_installation_id, int):
            token = self.get_installation_token(token_or_installation_id)
        else:
            token = token_or_installation_id

        url = "https://api.github.com/installation/repositories"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            repos: list[dict[str, Any]] = data.get("repositories", [])
            logger.info("Total authorized repos: %d", len(repos))
            for repo in repos:
                logger.debug(
                    "- Name: %s | Private: %s | Default Branch: %s",
                    repo.get("full_name"),
                    repo.get("private"),
                    repo.get("default_branch"),
                )
            return repos
        except requests.RequestException as exc:
            status_code = getattr(exc.response, "status_code", None)
            raise GitHubAppApiError(
                f"Failed to list authorized repositories: {exc}",
                status_code=status_code,
            ) from exc

    def get_repo_installation_id(self, owner: str, repo: str) -> int | None:
        """Find the GitHub App installation ID for a specific repository using App JWT.

        Args:
            owner (str): Repository owner or organization.
            repo (str): Repository name.

        Returns:
            int | None: Installation ID if found, None otherwise.
        """
        try:
            jwt_token = self.create_app_jwt()
            url = f"https://api.github.com/repos/{owner}/{repo}/installation"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Source-Context-Backend",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data: dict[str, Any] = resp.json()
                inst_id = data.get("id")
                if isinstance(inst_id, int):
                    return inst_id
        except Exception as exc:
            logger.debug(
                "Dynamic repo installation lookup for %s/%s encountered: %s",
                owner,
                repo,
                exc,
            )
        return None

    def get_repo_details(
        self,
        owner: str,
        repo: str,
        token_or_installation_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Fetch details of a specific repository.

        Args:
            owner (str): Repository owner or organization.
            repo (str): Repository name.
            token_or_installation_id (str | int | None, optional): Token or installation ID for auth. Defaults to None.

        Returns:
            dict[str, Any]: Repository details dictionary.

        Raises:
            GitHubAppApiError: If the request fails.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }
        if token_or_installation_id is not None:
            if isinstance(token_or_installation_id, int):
                token = self.get_installation_token(token_or_installation_id)
            else:
                token = token_or_installation_id
            headers["Authorization"] = f"Bearer {token}"

        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except requests.RequestException as exc:
            status_code = getattr(exc.response, "status_code", None)
            raise GitHubAppApiError(
                f"Failed to get details for repository {owner}/{repo}: {exc}",
                status_code=status_code,
            ) from exc

    def get_repo_languages(
        self,
        owner: str,
        repo: str,
        token_or_installation_id: str | int | None = None,
    ) -> dict[str, int]:
        """Fetch programming languages byte count for a repository.

        Args:
            owner (str): Repository owner or organization.
            repo (str): Repository name.
            token_or_installation_id (str | int | None, optional): Token or installation ID. Defaults to None.

        Returns:
            dict[str, int]: Mapping of language name to byte count.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }
        if token_or_installation_id is not None:
            if isinstance(token_or_installation_id, int):
                token = self.get_installation_token(token_or_installation_id)
            else:
                token = token_or_installation_id
            headers["Authorization"] = f"Bearer {token}"

        url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data: dict[str, int] = response.json()
            return data
        except requests.RequestException:
            return {}

    def list_branches(
        self,
        owner: str,
        repo: str,
        token_or_installation_id: str | int | None = None,
        *,
        installation_id: int | None = None,
        token: str | None = None,
    ) -> list[str]:
        """List all branch names for a repository.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            token_or_installation_id (str | int | None, optional): Token or installation ID. Defaults to None.
            installation_id (int | None, optional): Explicit installation ID keyword argument. Defaults to None.
            token (str | None, optional): Explicit token keyword argument. Defaults to None.

        Returns:
            list[str]: List of branch names.
        """
        auth_target = token or installation_id or token_or_installation_id
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }
        if auth_target is not None:
            if isinstance(auth_target, int):
                auth_token = self.get_installation_token(auth_target)
            else:
                auth_token = auth_target
            headers["Authorization"] = f"Bearer {auth_token}"

        branches: list[str] = []
        page = 1
        while True:
            url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100&page={page}"
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    break
                for item in data:
                    if isinstance(item, dict) and "name" in item:
                        branches.append(str(item["name"]))
                if len(data) < 100:
                    break
                page += 1
            except requests.RequestException as exc:
                logger.warning(
                    "Error fetching branches for %s/%s (page %d): %s",
                    owner,
                    repo,
                    page,
                    exc,
                )
                break

        return branches or ["main", "master"]

    def get_branch_commit_sha(
        self,
        owner: str,
        repo: str,
        branch: str,
        token_or_installation_id: str | int | None = None,
        *,
        installation_id: int | None = None,
        token: str | None = None,
    ) -> str | None:
        """Fetch the latest commit SHA for a specific branch.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            branch (str): Branch name.
            token_or_installation_id (str | int | None, optional): Token or installation ID. Defaults to None.
            installation_id (int | None, optional): Explicit installation ID keyword argument. Defaults to None.
            token (str | None, optional): Explicit token keyword argument. Defaults to None.

        Returns:
            str | None: Commit SHA if found, None otherwise.
        """
        auth_target = token or installation_id or token_or_installation_id
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }
        if auth_target is not None:
            if isinstance(auth_target, int):
                auth_token = self.get_installation_token(auth_target)
            else:
                auth_token = auth_target
            headers["Authorization"] = f"Bearer {auth_token}"

        url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            commit_obj = data.get("commit")
            if isinstance(commit_obj, dict) and "sha" in commit_obj:
                return str(commit_obj["sha"])
        except requests.RequestException as exc:
            logger.warning(
                "Could not get commit SHA for %s/%s branch %s: %s",
                owner,
                repo,
                branch,
                exc,
            )
        return None

    def get_repo_profile(
        self,
        owner: str,
        repo: str,
        branch: str | None = None,
        token_or_installation_id: str | int | None = None,
        *,
        installation_id: int | None = None,
        token: str | None = None,
    ) -> RepoProfileResult:
        """Extracts technical profile for a repository using GitHub API (Zero-Clone).

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            branch (str | None, optional): Target branch. If None, resolves default branch. Defaults to None.
            token_or_installation_id (str | int | None, optional): Token or installation ID. Defaults to None.
            installation_id (int | None, optional): Explicit installation ID keyword argument. Defaults to None.
            token (str | None, optional): Explicit token keyword argument. Defaults to None.

        Returns:
            RepoProfileResult: Technical profile extracted via GitHub API.
        """
        auth_target = token or installation_id or token_or_installation_id
        resolved_token: str | None = None
        if isinstance(auth_target, int):
            resolved_token = self.get_installation_token(auth_target)
        elif isinstance(auth_target, str):
            resolved_token = auth_target

        details = self.get_repo_details(
            owner, repo, token_or_installation_id=auth_target
        )
        target_branch = branch or details.get("default_branch", "main")
        description = details.get("description")

        commit_sha = (
            self.get_branch_commit_sha(
                owner,
                repo,
                target_branch,
                token_or_installation_id=auth_target,
            )
            or "HEAD"
        )

        return RepoProfileService().profile_github_repository(
            owner=owner,
            repo=repo,
            branch=target_branch,
            token=resolved_token,
            commit_sha=commit_sha,
            summary=description,
        )

    def build_authenticated_clone_url(self, git_url: str, token: str) -> str:
        """Build an authenticated clone URL using x-access-token for GitHub.

        Args:
            git_url (str): Original Git clone URL.
            token (str): Installation access token.

        Returns:
            str: Authenticated URL in the format https://x-access-token:{token}@github.com/{owner}/{repo}.git.

        Raises:
            ValueError: If the repository URL is not a recognized GitHub URL.
        """
        clean_url = git_url.strip()
        # Handle SSH style git@github.com:owner/repo.git
        if clean_url.startswith("git@github.com:"):
            path = clean_url.split("git@github.com:", 1)[1]
        else:
            parsed = urlparse(clean_url)
            path = parsed.path.lstrip("/")

        path = path.removesuffix(".git")
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub repository URL: {git_url}")

        owner = parts[0]
        repo = parts[1]
        return f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"

    def clone_private_repo(
        self,
        owner: str,
        repo: str,
        token: str,
        target_dir: str | Path,
        branch: str | None = None,
        depth: int = 1,
    ) -> GitRepositoryMetadata:
        """Clone a private repository to local directory using x-access-token.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            token (str): Installation access token.
            target_dir (str | Path): Local target destination.
            branch (str | None, optional): Specific branch name. Defaults to None.
            depth (int, optional): Shallow clone depth. Defaults to 1.

        Returns:
            GitRepositoryMetadata: Cloned repository metadata.

        Raises:
            GitCommandError: If the Git clone command fails.
        """
        dest_path = Path(target_dir).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)

        auth_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
        cmd = ["clone", "--depth", str(depth), "--single-branch"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([auth_url, str(dest_path)])

        self._run_git(cmd)

        # Sanitize remote URL to clean URL so the token doesn't persist on disk
        clean_url = f"https://github.com/{owner}/{repo}.git"
        self._run_git(
            ["-C", str(dest_path), "config", "remote.origin.url", clean_url],
            check=False,
        )

        commit_sha = self._run_git(
            ["-C", str(dest_path), "rev-parse", "HEAD"]
        ).stdout.strip()
        return GitRepositoryMetadata(
            repository_root=dest_path,
            branch=branch,
            commit_sha=commit_sha,
            remote_url=clean_url,
        )

    def download_repo_tarball(
        self,
        owner: str,
        repo: str,
        branch: str,
        token: str,
        output_path: str | Path,
    ) -> Path:
        """Download repository source code as a compressed tarball (.tar.gz).

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            branch (str): Target branch.
            token (str): Installation access token.
            output_path (str | Path): Local destination file path.

        Returns:
            Path: Resolved output path of the downloaded tarball.

        Raises:
            GitHubAppApiError: If the download request fails.
        """
        dest = Path(output_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://api.github.com/repos/{owner}/{repo}/tarball/{branch}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }

        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info("Downloaded repo tarball to %s", dest)
            return dest
        except requests.RequestException as exc:
            status_code = getattr(exc.response, "status_code", None)
            raise GitHubAppApiError(
                f"Failed to download tarball for {owner}/{repo}@{branch}: {exc}",
                status_code=status_code,
            ) from exc

    def clone_or_update_branch(
        self,
        repository_url: str,
        branch_name: str,
        destination: Path,
        installation_id: int | None = None,
    ) -> GitRepositoryMetadata:
        """Clone a specific branch into destination, or fetch latest if already present.

        Supports private GitHub repositories via installation_id and sanitizes remote origin
        URL on disk to avoid storing short-lived credentials.

        Args:
            repository_url (str): Git clone URL.
            branch_name (str): Target branch name.
            destination (Path): Path where the repository branch should be stored.
            installation_id (int | None, optional): GitHub App installation ID. Defaults to None.

        Returns:
            GitRepositoryMetadata: Repository metadata containing commit_sha and root path.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)

        token: str | None = None
        if installation_id is not None:
            token = self.get_installation_token(installation_id)

        target_clone_url = (
            self.build_authenticated_clone_url(repository_url, token)
            if token is not None
            else repository_url
        )

        clean_remote_url = repository_url.strip()

        if not destination.exists():
            try:
                self._run_git(
                    [
                        "clone",
                        "--depth",
                        "1",
                        "--single-branch",
                        "--branch",
                        branch_name,
                        target_clone_url,
                        str(destination),
                    ]
                )
                # Sanitize remote URL on disk
                self._run_git(
                    [
                        "-C",
                        str(destination),
                        "config",
                        "remote.origin.url",
                        clean_remote_url,
                    ],
                    check=False,
                )
            except Exception:
                if destination.exists():
                    shutil.rmtree(destination, ignore_errors=True)
                raise
        else:
            try:
                # Fetch latest commits using authenticated URL if private
                fetch_source = target_clone_url if token is not None else "origin"
                self._run_git(
                    [
                        "-C",
                        str(destination),
                        "fetch",
                        fetch_source,
                        branch_name,
                        "--depth",
                        "1",
                    ],
                    check=False,
                )
                self._run_git(
                    [
                        "-C",
                        str(destination),
                        "reset",
                        "--hard",
                        "FETCH_HEAD",
                    ],
                    check=False,
                )
            except Exception as exc:
                logger.warning(
                    "Error during git fetch/reset for %s: %s", destination, exc
                )

        commit_sha = self._run_git(
            ["-C", str(destination), "rev-parse", "HEAD"]
        ).stdout.strip()

        return GitRepositoryMetadata(
            repository_root=destination,
            branch=branch_name,
            commit_sha=commit_sha,
            remote_url=clean_remote_url,
        )

    def _run_git(
        self,
        arguments: Sequence[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a git command using subprocess safely without a shell.

        Args:
            arguments (Sequence[str]): Git arguments.
            check (bool, optional): Whether to raise on non-zero exit code. Defaults to True.

        Returns:
            subprocess.CompletedProcess[str]: Completed process result.

        Raises:
            GitExecutableNotFoundError: If git is not installed.
            GitCommandTimeoutError: If the command times out.
            GitCommandError: If the command exits with non-zero code.
        """
        command = ["git", *arguments]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise GitExecutableNotFoundError() from exc
        except subprocess.TimeoutExpired as exc:
            raise GitCommandTimeoutError(command, self._timeout_seconds) from exc

        if check and result.returncode != 0:
            # Mask potential tokens in error output for safety
            sanitized_err = re.sub(
                r"x-access-token:[^@]+@", "x-access-token:***@", result.stderr
            )
            sanitized_cmd = [
                re.sub(r"x-access-token:[^@]+@", "x-access-token:***@", arg)
                for arg in command
            ]
            raise GitCommandError(sanitized_cmd, result.returncode, sanitized_err)

        return result


# Standalone alias for consistency
RepositoryManagerV2 = RepoManagerV2

# ==============================================================================
# CONVENIENCE STANDALONE FUNCTIONS (KHỚP THEO QUY TRÌNH HƯỚNG DẪN CỦA USER)
# ==============================================================================


def get_installation_token(installation_id: int) -> str:
    """Tạo Installation Access Token từ installation_id bằng GitHub App credentials.

    Args:
        installation_id (int): ID của GitHub App installation.

    Returns:
        str: Token truy cập có thời hạn 1 giờ (dạng ghs_...).
    """
    manager = RepoManagerV2()
    return manager.get_installation_token(installation_id)


def list_authorized_repos(token: str) -> list[dict[str, Any]]:
    """Lấy danh sách tất cả các repo được cấp phép trong installation.

    Args:
        token (str): Installation access token.

    Returns:
        list[dict[str, Any]]: Danh sách các repository.
    """
    manager = RepoManagerV2()
    return manager.list_authorized_repos(token)


def get_repo_details(owner: str, repo: str, token: str) -> dict[str, Any]:
    """Xem chi tiết một repository cụ thể từ GitHub API.

    Args:
        owner (str): Chủ sở hữu repository (user hoặc org).
        repo (str): Tên repository.
        token (str): Installation access token.

    Returns:
        dict[str, Any]: Chi tiết thông tin repository.
    """
    manager = RepoManagerV2()
    return manager.get_repo_details(owner, repo, token)


def clone_private_repo(
    owner: str,
    repo: str,
    token: str,
    target_dir: str,
    branch: str | None = None,
    depth: int = 1,
) -> GitRepositoryMetadata:
    """Clone private repository về thư mục đích sử dụng x-access-token.

    Args:
        owner (str): Chủ sở hữu repository.
        repo (str): Tên repository.
        token (str): Installation access token.
        target_dir (str): Thư mục đích trên máy chủ.
        branch (str | None, optional): Nhánh cần clone. Defaults to None.
        depth (int, optional): Độ sâu commit. Defaults to 1.

    Returns:
        GitRepositoryMetadata: Thông tin commit và đường dẫn của repo vừa clone.
    """
    manager = RepoManagerV2()
    return manager.clone_private_repo(
        owner=owner,
        repo=repo,
        token=token,
        target_dir=target_dir,
        branch=branch,
        depth=depth,
    )


def download_repo_tarball(
    owner: str, repo: str, branch: str, token: str, output_path: str
) -> Path:
    """Tải trực tiếp source code dạng nén (.tar.gz) về máy chủ không cần cài git.

    Args:
        owner (str): Chủ sở hữu repository.
        repo (str): Tên repository.
        branch (str): Tên branch.
        token (str): Installation access token.
        output_path (str): Đường dẫn lưu file nén.

    Returns:
        Path: Đường dẫn file đã lưu.
    """
    manager = RepoManagerV2()
    return manager.download_repo_tarball(
        owner=owner,
        repo=repo,
        branch=branch,
        token=token,
        output_path=output_path,
    )


def get_repo_profile(
    owner: str,
    repo: str,
    branch: str | None = None,
    token: str | None = None,
    installation_id: int | None = None,
) -> RepoProfileResult:
    """Trích xuất thông tin kỹ thuật (tech stack, framework, commands) trực tiếp qua GitHub API.

    Args:
        owner (str): Chủ sở hữu repository.
        repo (str): Tên repository.
        branch (str | None, optional): Nhánh phân tích. Defaults to None (default branch).
        token (str | None, optional): Installation access token. Defaults to None.
        installation_id (int | None, optional): GitHub App installation ID. Defaults to None.

    Returns:
        RepoProfileResult: Hồ sơ kỹ thuật của repository.
    """
    manager = RepoManagerV2()
    return manager.get_repo_profile(
        owner=owner,
        repo=repo,
        branch=branch,
        token=token,
        installation_id=installation_id,
    )
