"""Integration tests for Indexing Job pipeline and status tracking."""

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
            await session.execute(text("DELETE FROM indexing_jobs;"))
            await session.execute(text("DELETE FROM projects;"))
            await session.execute(text("DELETE FROM branches;"))
            await session.execute(text("DELETE FROM repositories;"))
            await session.execute(text("DELETE FROM members;"))
            await session.execute(text("DELETE FROM workspaces;"))
            await session.execute(text("DELETE FROM users;"))

            user = User(
                username="indexer_owner",
                email="indexer_owner@example.com",
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
async def test_indexing_pipeline_trigger_and_status(client: TestClient) -> None:
    """Test creating workspace, repository, branches, and triggering branch indexing pipeline."""
    # 1. Create Workspace
    ws_res = client.post(
        "/api/v1/workspaces/",
        json={"workspace_name": "Pipeline Workspace", "description": "Test indexing"},
    )
    assert ws_res.status_code == status.HTTP_201_CREATED
    ws_id = ws_res.json()["id"]

    # 2. Create Repository with branch 'main'
    repo_payload = {
        "name": "fastapi-demo",
        "git_url": "https://github.com/fastapi/fastapi.git",
        "branches": [{"branch_name": "main", "commit_hashed": "HEAD"}],
    }
    repo_res = client.post(
        f"/api/v1/workspaces/{ws_id}/repositories", json=repo_payload
    )
    assert repo_res.status_code == status.HTTP_201_CREATED
    branch_id = repo_res.json()["branches"][0]["id"]

    # 3. Configure sub-project
    proj_res = client.post(
        f"/api/v1/workspaces/{ws_id}/branches/{branch_id}/projects",
        json={"root_dir": "backend", "language": "python"},
    )
    assert proj_res.status_code == status.HTTP_201_CREATED

    # 4. Trigger Branch Indexing
    trigger_res = client.post(f"/api/v1/workspaces/{ws_id}/branches/{branch_id}/index")
    assert trigger_res.status_code == status.HTTP_202_ACCEPTED
    job_data = trigger_res.json()
    assert job_data["branch_id"] == branch_id
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress_pct"] == 100

    # 5. List Indexing Jobs
    jobs_res = client.get(f"/api/v1/workspaces/{ws_id}/indexing-jobs")
    assert jobs_res.status_code == status.HTTP_200_OK
    assert len(jobs_res.json()) == 1
    assert jobs_res.json()[0]["status"] == "COMPLETED"
