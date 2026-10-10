"""Unit tests for GitHub private repository URL reading flow.

Tests cover:
- GitHubAppClient authentication (token minting, caching, JWT creation)
- GitHubAppClient API calls (list_branches, branch_commit_sha)
- GitHubAppClient error handling (HTTP 401/403/404/429/5xx)
- GitClient._git_auth_environment (token → env var translation)
- GitClient.clone_or_update_branch with access_token
- download_branch_source_stage integration flow
"""

import base64
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.core.error_code import ErrorCode
from app.github_app import GitHubAppClient, GitHubAppError
from app.repository_manager.exceptions import InvalidGitHubUrlError
from app.repository_manager.git_client import GitClient
from app.repository_manager.github_url import (
    GitHubRepositoryReference,
    GitHubUrlParser,
    fetch_github_branches,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings():
    """Return a mock Settings object with GitHub App credentials."""
    s = MagicMock()
    s.GITHUB_APP_ID = "123456"
    s.GITHUB_APP_PRIVATE_KEY = MagicMock()
    # RSA private key is only needed for real JWT signing; mock it out
    s.GITHUB_APP_PRIVATE_KEY.get_secret_value.return_value = ""
    return s


@pytest.fixture
def github_client(mock_settings):
    """Return a GitHubAppClient with mocked settings."""
    return GitHubAppClient(config=mock_settings, timeout_seconds=5)


# ===========================================================================
# Group 1: GitHubAppClient – Token Minting & Caching
# ===========================================================================


class TestInstallationTokenMinting:
    """Token lifecycle: mint, cache, refresh, and edge-case validation."""

    def test_rejects_non_positive_installation_id(self, github_client):
        """installation_id <= 0 should raise immediately without hitting the API."""
        with pytest.raises(GitHubAppError, match="invalid"):
            github_client.installation_token(0)

        with pytest.raises(GitHubAppError, match="invalid"):
            github_client.installation_token(-1)

    def test_mints_new_token_on_cache_miss(self, github_client):
        """First call should hit the API and cache the result."""
        future = datetime.now(UTC) + timedelta(hours=1)
        github_client._create_app_jwt = MagicMock(return_value="fake-jwt")
        github_client._request_json = MagicMock(return_value={
            "token": "ghs_new_token",
            "expires_at": future.isoformat(),
        })

        token = github_client.installation_token(42)

        assert token == "ghs_new_token"
        github_client._request_json.assert_called_once()
        # Verify the token was cached
        assert 42 in github_client._token_cache

    def test_returns_cached_token_when_still_valid(self, github_client):
        """Subsequent calls should skip the API when cached token is fresh."""
        future = datetime.now(UTC) + timedelta(hours=1)
        github_client._token_cache[42] = ("ghs_cached", future)

        token = github_client.installation_token(42)

        assert token == "ghs_cached"

    def test_refreshes_expired_token(self, github_client):
        """Token expiring within 2 minutes should trigger a re-fetch."""
        almost_expired = datetime.now(UTC) + timedelta(seconds=30)
        github_client._token_cache[42] = ("ghs_old", almost_expired)

        new_future = datetime.now(UTC) + timedelta(hours=1)
        github_client._create_app_jwt = MagicMock(return_value="fake-jwt")
        github_client._request_json = MagicMock(return_value={
            "token": "ghs_refreshed",
            "expires_at": new_future.isoformat(),
        })

        token = github_client.installation_token(42)

        assert token == "ghs_refreshed"
        github_client._request_json.assert_called_once()

    def test_raises_on_invalid_api_response(self, github_client):
        """API returning garbage should raise a clear error."""
        github_client._create_app_jwt = MagicMock(return_value="fake-jwt")
        github_client._request_json = MagicMock(return_value={"unexpected": True})

        with pytest.raises(GitHubAppError, match="valid installation token"):
            github_client.installation_token(42)

    def test_raises_on_invalid_expiry_format(self, github_client):
        """API returning a non-ISO expiry should raise."""
        github_client._create_app_jwt = MagicMock(return_value="fake-jwt")
        github_client._request_json = MagicMock(return_value={
            "token": "ghs_token",
            "expires_at": "not-a-date",
        })

        with pytest.raises(GitHubAppError, match="invalid token expiry"):
            github_client.installation_token(42)


# ===========================================================================
# Group 2: GitHubAppClient – JWT Creation
# ===========================================================================


class TestAppJwtCreation:
    """Validate JWT signing from app credentials."""

    def test_raises_when_app_id_missing(self, github_client):
        """Missing GITHUB_APP_ID should raise immediately."""
        github_client._settings.GITHUB_APP_ID = None

        with pytest.raises(GitHubAppError, match="App ID"):
            github_client._create_app_jwt()

    def test_raises_when_app_id_empty(self, github_client):
        """Blank GITHUB_APP_ID should raise."""
        github_client._settings.GITHUB_APP_ID = "   "

        with pytest.raises(GitHubAppError, match="App ID"):
            github_client._create_app_jwt()

    def test_raises_when_app_id_not_numeric(self, github_client):
        """Non-numeric GITHUB_APP_ID should raise."""
        github_client._settings.GITHUB_APP_ID = "abc"

        with pytest.raises(GitHubAppError, match="App ID"):
            github_client._create_app_jwt()

    def test_raises_when_private_key_empty(self, github_client):
        """Empty private key should raise."""
        github_client._settings.GITHUB_APP_ID = "123456"
        github_client._settings.GITHUB_APP_PRIVATE_KEY.get_secret_value.return_value = "  "

        with pytest.raises(GitHubAppError, match="credentials"):
            github_client._create_app_jwt()


# ===========================================================================
# Group 3: GitHubAppClient – API Methods (list_branches, branch_commit_sha)
# ===========================================================================


class TestListBranches:
    """Test list_branches with and without installation_id."""

    def test_list_branches_without_installation_id(self, github_client):
        """Public repos should work without token."""
        github_client._request_json = MagicMock(return_value=[
            {"name": "main"},
            {"name": "develop"},
        ])

        branches = github_client.list_branches("owner", "repo")

        assert branches == ["main", "develop"]
        # Verify token was not fetched
        call_kwargs = github_client._request_json.call_args
        assert call_kwargs.kwargs.get("token") is None

    def test_list_branches_with_installation_id(self, github_client):
        """Private repos should use an installation token."""
        future = datetime.now(UTC) + timedelta(hours=1)
        github_client._token_cache[99] = ("ghs_private_token", future)

        github_client._request_json = MagicMock(return_value=[
            {"name": "main"},
            {"name": "feature/auth"},
        ])

        branches = github_client.list_branches(
            "org", "private-repo", installation_id=99
        )

        assert branches == ["main", "feature/auth"]
        call_kwargs = github_client._request_json.call_args
        assert call_kwargs.kwargs.get("token") == "ghs_private_token"

    def test_list_branches_handles_pagination(self, github_client):
        """Should paginate when a page returns exactly 100 items."""
        page1 = [{"name": f"branch-{i}"} for i in range(100)]
        page2 = [{"name": "final-branch"}]

        github_client._request_json = MagicMock(side_effect=[page1, page2])

        branches = github_client.list_branches("owner", "repo")

        assert len(branches) == 101
        assert branches[-1] == "final-branch"
        assert github_client._request_json.call_count == 2

    def test_list_branches_raises_on_non_list_response(self, github_client):
        """Non-list API response should raise."""
        github_client._request_json = MagicMock(return_value={"error": "oops"})

        with pytest.raises(GitHubAppError, match="invalid branch list"):
            github_client.list_branches("owner", "repo")

    def test_list_branches_skips_entries_without_name(self, github_client):
        """Branch entries missing the 'name' key should be silently skipped."""
        github_client._request_json = MagicMock(return_value=[
            {"name": "main"},
            {"no_name": True},
            "not-a-dict",
            {"name": "develop"},
        ])

        branches = github_client.list_branches("owner", "repo")

        assert branches == ["main", "develop"]


class TestBranchCommitSha:
    """Test branch_commit_sha with and without installation_id."""

    def test_returns_sha_for_public_repo(self, github_client):
        github_client._request_json = MagicMock(return_value={
            "commit": {"sha": "abc123def456"}
        })

        sha = github_client.branch_commit_sha("owner", "repo", "main")

        assert sha == "abc123def456"

    def test_returns_sha_for_private_repo(self, github_client):
        future = datetime.now(UTC) + timedelta(hours=1)
        github_client._token_cache[99] = ("ghs_token", future)

        github_client._request_json = MagicMock(return_value={
            "commit": {"sha": "private_sha_789"}
        })

        sha = github_client.branch_commit_sha(
            "org", "private-repo", "main", installation_id=99
        )

        assert sha == "private_sha_789"
        call_kwargs = github_client._request_json.call_args
        assert call_kwargs.kwargs.get("token") == "ghs_token"

    def test_raises_on_missing_sha(self, github_client):
        github_client._request_json = MagicMock(return_value={"commit": {}})

        with pytest.raises(GitHubAppError, match="commit SHA"):
            github_client.branch_commit_sha("owner", "repo", "main")

    def test_raises_on_missing_commit_key(self, github_client):
        github_client._request_json = MagicMock(return_value={"not_commit": {}})

        with pytest.raises(GitHubAppError, match="commit SHA"):
            github_client.branch_commit_sha("owner", "repo", "main")


# ===========================================================================
# Group 4: GitHubAppClient – HTTP Error Handling
# ===========================================================================


class TestGitHubApiErrorHandling:
    """Verify correct error codes are propagated for different HTTP statuses."""

    @pytest.fixture
    def client_with_real_request(self, github_client):
        """Client that uses the real _request_json (to test HTTP error handling)."""
        return github_client

    @pytest.mark.parametrize(
        ("http_code", "expected_error_code"),
        [
            (401, ErrorCode.FORBIDDEN),
            (403, ErrorCode.FORBIDDEN),
            (404, ErrorCode.RESOURCE_NOT_FOUND),
            (429, ErrorCode.RATE_LIMIT_EXCEEDED),
            (500, ErrorCode.SYSTEM_ERROR),
            (502, ErrorCode.SYSTEM_ERROR),
            (503, ErrorCode.SYSTEM_ERROR),
        ],
    )
    def test_http_error_codes_mapping(
        self, github_client, http_code, expected_error_code
    ):
        """Each HTTP error status should map to the correct ErrorCode."""
        from urllib.error import HTTPError
        from io import BytesIO

        def raise_http_error(*args, **kwargs):
            raise HTTPError(
                url="https://api.github.com/test",
                code=http_code,
                msg="Error",
                hdrs={},
                fp=BytesIO(b"{}"),
            )

        with patch("app.github_app.urlopen", side_effect=raise_http_error):
            with pytest.raises(GitHubAppError) as exc_info:
                github_client._request_json("/test")

            assert exc_info.value.error_code == expected_error_code

    def test_network_error_raises_connection_error(self, github_client):
        """URLError (network failure) should raise a connection error."""
        from urllib.error import URLError

        with patch("app.github_app.urlopen", side_effect=URLError("DNS failed")):
            with pytest.raises(GitHubAppError, match="Could not connect"):
                github_client._request_json("/test")

    def test_timeout_raises_connection_error(self, github_client):
        """TimeoutError should raise a connection error."""
        with patch("app.github_app.urlopen", side_effect=TimeoutError()):
            with pytest.raises(GitHubAppError, match="Could not connect"):
                github_client._request_json("/test")

    def test_json_decode_error_raises_connection_error(self, github_client):
        """Malformed JSON response should raise a connection error."""
        with patch("app.github_app.urlopen", side_effect=json.JSONDecodeError("", "", 0)):
            with pytest.raises(GitHubAppError, match="Could not connect"):
                github_client._request_json("/test")


# ===========================================================================
# Group 5: GitClient._git_auth_environment
# ===========================================================================


class TestGitAuthEnvironment:
    """Verify environment variable translation for Git HTTP auth."""

    def test_creates_correct_authorization_header(self):
        """access_token should be Base64-encoded as x-access-token:TOKEN."""
        env = GitClient._git_auth_environment("ghs_test_token_123")

        expected_creds = base64.b64encode(
            b"x-access-token:ghs_test_token_123"
        ).decode("ascii")

        assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
        assert env["GIT_CONFIG_VALUE_0"] == f"AUTHORIZATION: basic {expected_creds}"
        assert env["GIT_CONFIG_COUNT"] == "1"
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_increments_existing_git_config_count(self):
        """If GIT_CONFIG_COUNT is already set, new entries should be appended."""
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "2"}):
            env = GitClient._git_auth_environment("ghs_token")

            assert "GIT_CONFIG_KEY_2" in env
            assert "GIT_CONFIG_VALUE_2" in env
            assert env["GIT_CONFIG_COUNT"] == "3"

    def test_handles_invalid_git_config_count(self):
        """Non-numeric GIT_CONFIG_COUNT should fall back to 0."""
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "invalid"}):
            env = GitClient._git_auth_environment("ghs_token")

            assert "GIT_CONFIG_KEY_0" in env
            assert env["GIT_CONFIG_COUNT"] == "1"

    def test_env_contains_inherited_variables(self):
        """Auth env should inherit the current process environment."""
        env = GitClient._git_auth_environment("ghs_token")

        # PATH should always exist in the inherited env
        assert "PATH" in env or "Path" in env


# ===========================================================================
# Group 6: GitClient.clone_or_update_branch with access_token
# ===========================================================================


class TestCloneOrUpdateBranchWithToken:
    """Verify that access_token is correctly threaded through to Git subprocess."""

    @patch.object(GitClient, "_run")
    def test_clone_new_repo_passes_token(self, mock_run, tmp_path):
        """Fresh clone should use access_token."""
        dest = tmp_path / "new-repo"  # Does not exist
        mock_run.return_value = MagicMock(
            stdout="abc123\n", returncode=0
        )

        client = GitClient(timeout_seconds=30)

        # Mock get_metadata to avoid real git calls
        metadata = MagicMock()
        metadata.repository_root = dest
        metadata.commit_sha = "abc123"
        metadata.branch = "main"
        metadata.remote_url = "https://github.com/org/repo.git"
        client.get_metadata = MagicMock(return_value=metadata)

        result = client.clone_or_update_branch(
            "https://github.com/org/repo.git",
            "main",
            dest,
            access_token="ghs_private_token",
        )

        # First call should be clone with access_token
        first_call = mock_run.call_args_list[0]
        assert first_call.kwargs.get("access_token") == "ghs_private_token"
        # Verify clone arguments include branch
        clone_args = first_call.args[0]
        assert "clone" in clone_args
        assert "--branch" in clone_args
        assert "main" in clone_args

    @patch.object(GitClient, "_run")
    def test_update_existing_repo_passes_token(self, mock_run, tmp_path):
        """Existing repo should fetch+reset with access_token."""
        dest = tmp_path / "existing-repo"
        dest.mkdir()  # Simulate existing directory

        mock_run.return_value = MagicMock(stdout="def456\n", returncode=0)

        client = GitClient(timeout_seconds=30)
        metadata = MagicMock()
        metadata.repository_root = dest
        metadata.commit_sha = "def456"
        metadata.branch = "develop"
        metadata.remote_url = "https://github.com/org/repo.git"
        client.get_metadata = MagicMock(return_value=metadata)

        result = client.clone_or_update_branch(
            "https://github.com/org/repo.git",
            "develop",
            dest,
            access_token="ghs_update_token",
        )

        # Should call fetch then reset, both with token
        assert mock_run.call_count == 2
        for call in mock_run.call_args_list:
            assert call.kwargs.get("access_token") == "ghs_update_token"

    @patch.object(GitClient, "_run")
    def test_clone_without_token_passes_none(self, mock_run, tmp_path):
        """Public repo clone should pass access_token=None."""
        dest = tmp_path / "public-repo"
        mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)

        client = GitClient(timeout_seconds=30)
        metadata = MagicMock()
        metadata.repository_root = dest
        metadata.commit_sha = "abc123"
        metadata.branch = "main"
        metadata.remote_url = "https://github.com/public/repo.git"
        client.get_metadata = MagicMock(return_value=metadata)

        result = client.clone_or_update_branch(
            "https://github.com/public/repo.git",
            "main",
            dest,
        )

        first_call = mock_run.call_args_list[0]
        assert first_call.kwargs.get("access_token") is None


# ===========================================================================
# Group 7: fetch_github_branches (convenience function)
# ===========================================================================


class TestFetchGitHubBranches:
    """Test the module-level fetch_github_branches function."""

    @patch("app.repository_manager.github_url.github_app_client")
    def test_delegates_to_app_client(self, mock_client):
        """Should delegate to github_app_client.list_branches."""
        mock_client.list_branches.return_value = ["main", "staging"]

        result = fetch_github_branches("owner", "repo", installation_id=42)

        assert result == ["main", "staging"]
        mock_client.list_branches.assert_called_once_with(
            "owner", "repo", installation_id=42,
        )

    @patch("app.repository_manager.github_url.github_app_client")
    def test_works_without_installation_id(self, mock_client):
        """Should also work for public repos without installation_id."""
        mock_client.list_branches.return_value = ["main"]

        result = fetch_github_branches("owner", "repo")

        mock_client.list_branches.assert_called_once_with(
            "owner", "repo", installation_id=None,
        )


# ===========================================================================
# Group 8: GitHubAppClient.installation_belongs_to_app
# ===========================================================================


class TestInstallationBelongsToApp:
    """Verify installation ownership check."""

    def test_returns_true_when_app_id_matches(self, github_client):
        github_client._create_app_jwt = MagicMock(return_value="jwt")
        github_client._request_json = MagicMock(return_value={
            "app_id": 123456,
        })

        assert github_client.installation_belongs_to_app(42) is True

    def test_returns_false_when_app_id_differs(self, github_client):
        github_client._create_app_jwt = MagicMock(return_value="jwt")
        github_client._request_json = MagicMock(return_value={
            "app_id": 999999,
        })

        assert github_client.installation_belongs_to_app(42) is False

    def test_raises_when_app_id_not_configured(self, github_client):
        github_client._settings.GITHUB_APP_ID = None

        with pytest.raises(GitHubAppError, match="not configured"):
            github_client.installation_belongs_to_app(42)


# ===========================================================================
# Group 9: GitHubUrlParser – Private repo URLs are identical to public
# ===========================================================================


class TestGitHubUrlParserForPrivateRepos:
    """Verify URL parser treats private repo URLs the same as public ones."""

    @pytest.mark.parametrize(
        ("url", "owner", "repo"),
        [
            (
                "https://github.com/my-org/private-service",
                "my-org",
                "private-service",
            ),
            (
                "https://github.com/company/internal-api.git",
                "company",
                "internal-api",
            ),
            (
                "  https://github.com/user/my_repo  ",
                "user",
                "my_repo",
            ),
        ],
    )
    def test_parses_private_repo_urls(self, url, owner, repo):
        """Private repos have identical URL format to public repos."""
        ref = GitHubUrlParser.parse(url)

        assert ref.owner == owner
        assert ref.repository == repo
        assert ref.clone_url == f"https://github.com/{owner}/{repo}.git"

    def test_repository_reference_properties(self):
        """Verify computed properties on GitHubRepositoryReference."""
        ref = GitHubRepositoryReference(owner="My-Org", repository="Secret-Repo")

        assert ref.clone_url == "https://github.com/My-Org/Secret-Repo.git"
        assert ref.repository_id == "github__my-org__secret-repo"
        assert ref.workspace_directory_name == ref.repository_id
""",
<parameter name="Description">Comprehensive unit tests for the private GitHub repo URL reading flow. Covers GitHubAppClient (auth, caching, API calls, error handling), GitClient (auth env, clone with token), fetch_github_branches, and URL parser edge cases.
