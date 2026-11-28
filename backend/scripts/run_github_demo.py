from pathlib import Path

from app.repository_manager.git_client import GitClient

REPOSITORY_WORKSPACE_ROOT = "./workspace-repositories"
OWNER = "HieuITMHG"
REPOSITORY = "project-csa"
BASE_WORKSPACE = Path(REPOSITORY_WORKSPACE_ROOT).resolve()
destination = BASE_WORKSPACE / "test_repo" / "master"
print(destination)
# res = github_url.fetch_github_branches(owner=OWNER, repository=REPOSITORY)

# print(res)

print("============= Clone thu repo truyen thon ================")

git_client = GitClient()
git_url = "https://github.com/HieuITMHG/project-csa.git"

metadata = git_client.clone_or_update_branch(
    repository_url=git_url, branch_name="master", destination=destination
)

print(metadata)
