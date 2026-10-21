"""Unit tests for repository profile extraction."""

from pathlib import Path
import pytest

from app.repository_manager_v2.profile_extractor import (
    LocalDiskSourceProvider,
    PythonProfileExtractor,
    RepoProfileService,
)
from app.repository_manager_v2 import post_download_metadata_hook


def test_python_profile_extractor_mock(tmp_path: Path) -> None:
    """Tests PythonProfileExtractor extracting metadata from a synthetic Python repo."""
    # Create sample pyproject.toml
    pyproject_content = """
[project]
name = "sample-service"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "sqlalchemy>=2.0.0",
    "celery>=5.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
]

[tool.ruff]
line-length = 88
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sample Service", encoding="utf-8")

    # Create directory structure
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("print('Hello')", encoding="utf-8")
    (app_dir / "api").mkdir()
    (app_dir / "services").mkdir()
    (app_dir / "model").mkdir()

    provider = LocalDiskSourceProvider(tmp_path)
    extractor = PythonProfileExtractor()

    assert extractor.can_handle(provider) is True

    result = extractor.extract(provider)

    assert result.primary_language == "python"
    assert result.project_type == "fastapi_api"
    assert result.tech_stack.package_manager == "uv"
    assert "FastAPI" in result.tech_stack.frameworks
    assert "SQLAlchemy" in result.tech_stack.orm
    assert "Celery" in result.tech_stack.task_queues
    assert "pytest" in result.tech_stack.test_frameworks
    assert "Ruff" in result.tech_stack.linters
    assert "app/main.py" in result.key_entrypoints
    assert "app/api" in result.directory_map
    assert "app/services" in result.directory_map
    assert "app/model" in result.directory_map
    assert result.dev_commands.run == "uvicorn app.main:app --reload"
    assert result.dev_commands.test == "pytest"
    assert result.dev_commands.lint == "ruff check ."
    assert result.coding_conventions.linter == "ruff"
    assert result.coding_conventions.strict_typing is True
    assert result.metrics.has_readme is True
    assert result.metrics.readme_file == "README.md"


def test_repo_profile_service_and_legacy_hook(tmp_path: Path) -> None:
    """Tests RepoProfileService and post_download_metadata_hook compatibility."""
    (tmp_path / "requirements.txt").write_text(
        "django>=4.2\npsycopg2-binary\n", encoding="utf-8"
    )
    (tmp_path / "manage.py").write_text("# Django manage", encoding="utf-8")

    service = RepoProfileService()
    profile = service.profile_directory(tmp_path)

    assert profile.primary_language == "python"
    assert profile.project_type == "django_app"
    assert "Django" in profile.tech_stack.frameworks
    assert "manage.py" in profile.key_entrypoints
    assert profile.dev_commands.run == "python manage.py runserver"

    # Test legacy hook backward compatibility
    legacy_res = post_download_metadata_hook(
        destination=tmp_path,
        repository_url="https://github.com/example/sample",
        branch_name="main",
        commit_sha="abc1234",
    )

    assert legacy_res["primary_language"] == "python"
    assert legacy_res["project_type"] == "django_app"
    assert legacy_res["branch_name"] == "main"
    assert legacy_res["commit_sha"] == "abc1234"
    assert legacy_res["file_count"] == 2
    assert "requirements.txt" in legacy_res["detected_manifests"]


def test_github_api_profile_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests Zero-Clone profile extraction using GitHub API with mocked responses."""
    import base64
    import requests

    tree_payload = {
        "tree": [
            {"path": "pyproject.toml", "type": "blob", "size": 120},
            {"path": "uv.lock", "type": "blob", "size": 50},
            {"path": "README.md", "type": "blob", "size": 200},
            {"path": "app", "type": "tree"},
            {"path": "app/main.py", "type": "blob", "size": 80},
            {"path": "app/api", "type": "tree"},
            {"path": "app/services", "type": "tree"},
        ]
    }

    pyproject_bytes = b"""
[project]
name = "api-microservice"
dependencies = [
    "fastapi>=0.110.0",
    "sqlalchemy>=2.0.0",
]
"""
    readme_bytes = (
        b"# API Microservice\n\nA high performance microservice for context retrieval."
    )

    def mock_get(url: str, *args: object, **kwargs: object) -> requests.Response:
        resp = requests.Response()
        resp.status_code = 200
        if "git/trees" in url:
            resp._content = __import__("json").dumps(tree_payload).encode("utf-8")
        elif "contents/pyproject.toml" in url:
            data = {
                "encoding": "base64",
                "content": base64.b64encode(pyproject_bytes).decode(),
            }
            resp._content = __import__("json").dumps(data).encode("utf-8")
        elif "contents/README.md" in url:
            data = {
                "encoding": "base64",
                "content": base64.b64encode(readme_bytes).decode(),
            }
            resp._content = __import__("json").dumps(data).encode("utf-8")
        else:
            resp.status_code = 404
        return resp

    monkeypatch.setattr(requests, "get", mock_get)

    service = RepoProfileService()
    profile = service.profile_github_repository(
        owner="test-org",
        repo="test-repo",
        branch="main",
        commit_sha="commit12345",
    )

    assert profile.primary_language == "python"
    assert profile.project_type == "fastapi_api"
    assert profile.tech_stack.package_manager == "uv"
    assert "FastAPI" in profile.tech_stack.frameworks
    assert "SQLAlchemy" in profile.tech_stack.orm
    assert "app/main.py" in profile.key_entrypoints
    assert "app/api" in profile.directory_map
    assert profile.dev_commands.run == "uvicorn app.main:app --reload"
    assert profile.metrics.total_files == 4
    assert profile.metrics.has_readme is True
    assert profile.summary == "A high performance microservice for context retrieval."
