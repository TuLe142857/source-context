"""Integration tests for Workspace Repository, Branch, and Sub-Project hierarchy APIs."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.dependencies import get_current_user
from app.core.postgres import database
from app.model.user import User


@pytest.fixture
def anyio_backend() -> str:
    """Fixture indicating anyio backend for async tests."""
    return "asyncio"


class TestState:
    """State helper for sharing current test user."""

    user: User | None = None


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    """Cleans up target test tables and inserts test user."""
    async with database.async_session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM projects;"))
            await session.execute(text("DELETE FROM branches;"))
            await session.execute(text("DELETE FROM repositories;"))
            await session.execute(text("DELETE FROM members;"))
            await session.execute(text("DELETE FROM workspaces;"))
            await session.execute(text("DELETE FROM users;"))

            user = User(
                username="ws_owner",
                email="ws_owner@example.com",
                hashed_password="fakehashowner",
                is_active="active",
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            TestState.user = user


@pytest.fixture(autouse=True)
def override_dependencies(application: FastAPI) -> None:
    """Overrides current user dependency in tests."""

    def get_test_user() -> User:
        if TestState.user is None:
            raise Exception("TestState.user is not set")
        return TestState.user

    application.dependency_overrides[get_current_user] = get_test_user


@pytest.mark.anyio
async def test_full_workspace_repository_branch_project_flow(
    client: TestClient,
) -> None:
    """Test full hierarchy creation: Workspace -> Repository -> Multiple Branches -> Sub-Projects."""
    # 1. Create Workspace
    ws_res = client.post(
        "/api/v1/workspaces/",
        json={
            "workspace_name": "SCIP Workspace",
            "description": "Testing SCIP targets",
        },
    )
    assert ws_res.status_code == status.HTTP_201_CREATED
    ws_id = ws_res.json()["id"]
    assert ws_res.json()["workspace_name"] == "SCIP Workspace"

    # 2. Inspect GitHub Branches (Mocked or real URL check)
    inspect_res = client.post(
        f"/api/v1/workspaces/{ws_id}/repositories/inspect-branches",
        json={"git_url": "https://github.com/fastapi/fastapi.git"},
    )
    assert inspect_res.status_code == status.HTTP_200_OK
    assert "branches" in inspect_res.json()
    assert len(inspect_res.json()["branches"]) > 0

    # 3. Create Repository with 2 selected branches ('main' and 'develop')
    repo_payload = {
        "name": "fastapi-repo",
        "git_url": "https://github.com/fastapi/fastapi.git",
        "branches": [
            {"branch_name": "main", "commit_hashed": "sha_main_123"},
            {"branch_name": "develop", "commit_hashed": "sha_dev_456"},
        ],
    }
    repo_res = client.post(
        f"/api/v1/workspaces/{ws_id}/repositories", json=repo_payload
    )
    assert repo_res.status_code == status.HTTP_201_CREATED
    repo_data = repo_res.json()
    assert repo_data["name"] == "fastapi-repo"
    assert len(repo_data["branches"]) == 2
    main_branch_id = repo_data["branches"][0]["id"]
    dev_branch_id = repo_data["branches"][1]["id"]
    assert (
        repo_data["branches"][0]["local_path"]
        == f"/app/workspace-repositories/ws_{ws_id}/fastapi-repo/main"
    )

    # 4. Configure Sub-Projects under 'main' branch (e.g. backend Python project)
    proj1_res = client.post(
        f"/api/v1/workspaces/{ws_id}/branches/{main_branch_id}/projects",
        json={"root_dir": "backend", "language": "python"},
    )
    assert proj1_res.status_code == status.HTTP_201_CREATED
    assert proj1_res.json()["root_dir"] == "backend"
    assert proj1_res.json()["language"] == "python"

    # Configure Sub-Project under 'develop' branch (e.g. docs TypeScript project)
    proj2_res = client.post(
        f"/api/v1/workspaces/{ws_id}/branches/{dev_branch_id}/projects",
        json={"root_dir": "docs", "language": "typescript"},
    )
    assert proj2_res.status_code == status.HTTP_201_CREATED
    proj2_id = proj2_res.json()["id"]

    # 5. Fetch Full Hierarchy
    hierarchy_res = client.get(f"/api/v1/workspaces/{ws_id}/hierarchy")
    assert hierarchy_res.status_code == status.HTTP_200_OK
    h_data = hierarchy_res.json()
    assert h_data["workspace_name"] == "SCIP Workspace"
    assert len(h_data["repositories"]) == 1
    assert len(h_data["repositories"][0]["branches"]) == 2

    # 6. Delete Sub-Project
    del_proj_res = client.delete(f"/api/v1/workspaces/{ws_id}/projects/{proj2_id}")
    assert del_proj_res.status_code == status.HTTP_204_NO_CONTENT
