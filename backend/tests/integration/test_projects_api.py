from collections.abc import Iterator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import text, select

from app.api.dependencies import get_current_user
from app.core.postgres import database
from app.domain.project import Project
from app.domain.member import Member
from app.domain.user import User
from app.enums.member_role import MemberRole


@pytest.fixture
def anyio_backend() -> str:
    """Fixture indicating anyio backend for async tests."""
    return "asyncio"


class TestState:
    """Dynamic test state sharing helper."""

    current_user: User | None = None
    owner: User | None = None
    invitee: User | None = None


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    """Cleans up target test tables and populates default test users."""
    async with database.async_session_factory() as session:
        async with session.begin():
            # Ordered deletes to avoid FK violations and exclusive lock hanging issues
            await session.execute(text("DELETE FROM repositories;"))
            await session.execute(text("DELETE FROM project_members;"))
            await session.execute(text("DELETE FROM projects;"))
            await session.execute(text("DELETE FROM users;"))

            # Create default owner and invitee
            owner = User(
                username="owner",
                email="owner@example.com",
                hashed_password="fakehashowner",
                is_active=True,
            )
            invitee = User(
                username="invitee",
                email="invitee@example.com",
                hashed_password="fakehashinvitee",
                is_active=True,
            )
            session.add_all([owner, invitee])
            await session.flush()

            await session.refresh(owner)
            await session.refresh(invitee)

            TestState.owner = owner
            TestState.invitee = invitee
            TestState.current_user = owner


@pytest.fixture(autouse=True)
def override_dependencies(application: FastAPI) -> Iterator[None]:
    """Overrides authenticated current user dependency during tests."""

    def get_current_test_user() -> User:
        if TestState.current_user is None:
            raise Exception("TestState.current_user is not set in test environment.")
        return TestState.current_user

    application.dependency_overrides[get_current_user] = get_current_test_user
    yield
    application.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_project(client: TestClient) -> None:
    """A user should be able to create a project and auto-become its Admin member."""
    payload = {"project_name": "Test Project", "description": "My first project"}
    response = client.post("/api/v1/projects/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["project_name"] == "Test Project"
    assert data["description"] == "My first project"
    assert "id" in data

    assert TestState.owner is not None
    owner_id = TestState.owner.id

    # Verify Database records
    async with database.async_session_factory() as session:
        # Check Project
        p_res = await session.execute(select(Project).where(Project.id == data["id"]))
        project = p_res.scalar_one()
        assert project.owner_id == owner_id

        # Check Member
        m_res = await session.execute(
            select(Member).where(
                Member.project_id == project.id, Member.user_id == owner_id
            )
        )
        member = m_res.scalar_one()
        assert member.role == MemberRole.ADMIN


@pytest.mark.anyio
async def test_list_projects(client: TestClient) -> None:
    """User list projects should return only projects they are associated with."""
    # 1. Create project 1 (owned by owner)
    payload_1 = {"project_name": "Owner Project"}
    res_1 = client.post("/api/v1/projects/", json=payload_1)
    project_1_id = res_1.json()["id"]

    # 2. Create project 2 (owned by invitee)
    TestState.current_user = TestState.invitee
    payload_2 = {"project_name": "Invitee Project"}
    res_2 = client.post("/api/v1/projects/", json=payload_2)
    project_2_id = res_2.json()["id"]

    # Test as owner: should only see Owner Project (Project 1)
    TestState.current_user = TestState.owner
    list_res = client.get("/api/v1/projects/")
    assert list_res.status_code == status.HTTP_200_OK
    projects = list_res.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project_1_id

    # Invite owner to Invitee Project
    TestState.current_user = TestState.invitee
    invite_payload = {"email": "owner@example.com", "role": "Viewer"}
    invite_res = client.post(
        f"/api/v1/projects/{project_2_id}/members/invite", json=invite_payload
    )
    assert invite_res.status_code == status.HTTP_201_CREATED

    # Test as owner again: should see both projects now
    TestState.current_user = TestState.owner
    list_res2 = client.get("/api/v1/projects/")
    assert len(list_res2.json()) == 2


@pytest.mark.anyio
async def test_get_project_detail_and_access(client: TestClient) -> None:
    """Project details should be accessible only by members or owners."""
    payload = {"project_name": "Private Project"}
    response = client.post("/api/v1/projects/", json=payload)
    project_id = response.json()["id"]

    # Fetch detail as Owner (Access Granted)
    detail_res = client.get(f"/api/v1/projects/{project_id}")
    assert detail_res.status_code == status.HTTP_200_OK
    data = detail_res.json()
    assert data["project_name"] == "Private Project"
    assert "members" in data
    assert "repositories" in data

    # Fetch detail as Invitee (Access Denied / Forbidden)
    TestState.current_user = TestState.invitee
    denied_res = client.get(f"/api/v1/projects/{project_id}")
    assert denied_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_update_project_metadata(client: TestClient) -> None:
    """Project name and description can be updated by authorized members."""
    payload = {"project_name": "Old Project Name", "description": "Old desc"}
    response = client.post("/api/v1/projects/", json=payload)
    project_id = response.json()["id"]

    # Update metadata
    update_payload = {"project_name": "New Project Name", "description": "New desc"}
    update_res = client.patch(f"/api/v1/projects/{project_id}", json=update_payload)
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["project_name"] == "New Project Name"
    assert update_res.json()["description"] == "New desc"


@pytest.mark.anyio
async def test_invite_member_and_duplicates(client: TestClient) -> None:
    """A project admin can invite members, but cannot double-invite or invite unregistered emails."""
    # Create project
    proj_res = client.post(
        "/api/v1/projects/", json={"project_name": "Workspace Project"}
    )
    project_id = proj_res.json()["id"]

    # 1. Successful invitation
    invite_payload = {"email": "invitee@example.com", "role": "Developer"}
    invite_res = client.post(
        f"/api/v1/projects/{project_id}/members/invite", json=invite_payload
    )
    assert invite_res.status_code == status.HTTP_201_CREATED
    assert invite_res.json()["role"] == "Developer"
    assert invite_res.json()["user_email"] == "invitee@example.com"

    # 2. Duplicate invitation (400 Bad Request)
    duplicate_res = client.post(
        f"/api/v1/projects/{project_id}/members/invite", json=invite_payload
    )
    assert duplicate_res.status_code == status.HTTP_400_BAD_REQUEST

    # 3. Invitation of non-existent user (404 Not Found)
    missing_payload = {"email": "notfound@example.com", "role": "Viewer"}
    missing_res = client.post(
        f"/api/v1/projects/{project_id}/members/invite", json=missing_payload
    )
    assert missing_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_remove_member(client: TestClient) -> None:
    """Project admin can remove members, but cannot remove the owner."""
    proj_res = client.post("/api/v1/projects/", json={"project_name": "Project X"})
    project_id = proj_res.json()["id"]

    # Invite member
    client.post(
        f"/api/v1/projects/{project_id}/members/invite",
        json={"email": "invitee@example.com", "role": "Viewer"},
    )

    assert TestState.invitee is not None
    assert TestState.owner is not None

    # 1. Remove invitee (Success)
    remove_res = client.delete(
        f"/api/v1/projects/{project_id}/members/{TestState.invitee.id}"
    )
    assert remove_res.status_code == status.HTTP_200_OK

    # 2. Remove owner (Bad Request)
    remove_owner_res = client.delete(
        f"/api/v1/projects/{project_id}/members/{TestState.owner.id}"
    )
    assert remove_owner_res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.anyio
async def test_project_repositories_link(client: TestClient) -> None:
    """Authorized users can attach multiple repository links to projects with pending status."""
    proj_res = client.post("/api/v1/projects/", json={"project_name": "Project Y"})
    project_id = proj_res.json()["id"]

    # 1. Attach repository link
    repo_payload = {
        "name": "my-cool-repo",
        "git_url": "https://github.com/coolowner/coolrepo.git",
        "description": "Just a test repo",
        "default_branch": "develop",
    }
    repo_res = client.post(
        f"/api/v1/projects/{project_id}/repositories", json=repo_payload
    )
    assert repo_res.status_code == status.HTTP_201_CREATED
    data = repo_res.json()
    assert data["name"] == "my-cool-repo"
    assert data["status"] == "pending"
    repo_id = data["id"]

    # 2. List repository links
    list_res = client.get(f"/api/v1/projects/{project_id}/repositories")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    # 3. Detach repository link
    delete_res = client.delete(f"/api/v1/projects/{project_id}/repositories/{repo_id}")
    assert delete_res.status_code == status.HTTP_200_OK
