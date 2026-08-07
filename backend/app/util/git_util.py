import subprocess
from urllib.parse import urlparse

def get_latest_commit_hash(repo_url: str, branch_name: str):
    result = subprocess.check_output(
        ["git", "ls-remote", repo_url, branch_name],
        text=True
    )

    return result.split()[0] if result else None

def get_repo_name(repo_url: str) -> str:
    """
    Extract repository name from a Git repository URL.

    Supported examples:
        github.com/user/repo
        https://github.com/user/repo
        http://github.com/user/repo
        git@github.com:user/repo.git
        ssh://git@github.com/user/repo.git
        https://github.com/user/repo/
        https://github.com/user/repo.git

    Returns:
        Repository name without the .git suffix.

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

import tempfile
import asyncio
from pathlib import Path
from app.model import Repository
from app.model import Branch

async def prepare_data(branch: Branch, repo: Repository):

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        print(f"Tạo dir ảo tại {temp_dir}")

        print("Đang tải metadata Git...")

        clone_proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "--single-branch", "--branch", branch.branch_name, 
            repo.git_url, temp_dir,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await clone_proc.communicate()