import asyncio
import logging
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse

from app.model.branch import Branch
from app.model.repository import Repository

logger = logging.getLogger(__name__)


def get_latest_commit_hash(
    repo_url: str,
    branch_name: str,
    installation_id: int | None = None,
    token: str | None = None,
) -> str | None:
    """Gets the latest commit hash for a given remote branch.

    Supports both public and private GitHub repositories by leveraging RepoManagerV2
    when installation_id or token is provided, and falling back safely to git ls-remote.

    Args:
        repo_url (str): Remote Git repository URL.
        branch_name (str): Branch name to query.
        installation_id (int | None, optional): GitHub App installation ID. Defaults to None.
        token (str | None, optional): GitHub access token. Defaults to None.

    Returns:
        str | None: Commit hash or None if not found or on error.
    """
    # 1. If installation_id or token is provided, query via RepoManagerV2
    if installation_id or token:
        try:
            from app.repository_manager.github_url import GitHubUrlParser
            from app.repository_manager.repo_manager_v2 import RepoManagerV2

            ref = GitHubUrlParser.parse(repo_url)
            manager = RepoManagerV2()
            commit_sha = manager.get_branch_commit_sha(
                ref.owner,
                ref.repository,
                branch_name,
                installation_id=installation_id,
                token=token,
            )
            if commit_sha:
                return commit_sha
        except Exception as exc:
            logger.warning(
                "Failed to get commit SHA via authenticated RepoManagerV2 for %s: %s",
                repo_url,
                exc,
            )

    # 2. Try git ls-remote safely with auth token if available, or unauthenticated
    target_url = repo_url
    if token:
        try:
            from app.repository_manager.repo_manager_v2 import RepoManagerV2

            target_url = RepoManagerV2().build_authenticated_clone_url(repo_url, token)
        except Exception:
            target_url = repo_url
    elif installation_id:
        try:
            from app.repository_manager.repo_manager_v2 import RepoManagerV2

            manager = RepoManagerV2()
            inst_token = manager.get_installation_token(installation_id)
            target_url = manager.build_authenticated_clone_url(repo_url, inst_token)
        except Exception:
            target_url = repo_url

    try:
        proc = subprocess.run(
            ["git", "ls-remote", target_url, branch_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.split()[0]
    except Exception:
        pass

    # 3. Fallback for public GitHub repositories without git CLI credentials
    if not installation_id and not token:
        try:
            from app.repository_manager.github_url import GitHubUrlParser
            from app.repository_manager.repo_manager_v2 import RepoManagerV2

            ref = GitHubUrlParser.parse(repo_url)
            return RepoManagerV2().get_branch_commit_sha(
                ref.owner, ref.repository, branch_name
            )
        except Exception:
            pass

    return None


def get_repo_name(repo_url: str) -> str:
    """Extract repository name from a Git repository URL.

    Supported examples:
        github.com/user/repo
        https://github.com/user/repo
        http://github.com/user/repo
        git@github.com:user/repo.git
        ssh://git@github.com/user/repo.git
        https://github.com/user/repo/
        https://github.com/user/repo.git

    Returns:
        str: Repository name without the .git suffix.

    Raises:
        ValueError: If the URL is invalid.
    """
    repo_url = repo_url.strip()

    # SCP-style SSH URL: git@github.com:user/repo.git
    if ":" in repo_url and "://" not in repo_url and "@" in repo_url:
        path = repo_url.split(":", 1)[1]
    else:
        # Thêm scheme nếu thiếu
        if "://" not in repo_url:
            repo_url = "https://" + repo_url

        parsed = urlparse(repo_url)
        path = parsed.path

    path = path.strip("/")

    if not path:
        raise ValueError("Invalid repository URL")

    repo_name = path.split("/")[-1]

    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    if not repo_name:
        raise ValueError("Invalid repository URL")

    return repo_name


async def prepare_data(branch: Branch, repo: Repository) -> None:
    """Prepares and clones Git repository metadata temporarily for indexing.

    Args:
        branch (Branch): Target branch model.
        repo (Repository): Repository model.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        Path(temp_dir)
        clone_proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            "--single-branch",
            "--branch",
            branch.branch_name,
            repo.git_url,
            temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await clone_proc.communicate()
