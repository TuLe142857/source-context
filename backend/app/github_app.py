"""GitHub App authentication and read-only repository access."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import logging
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import jwt

from app.core.config import Settings, settings
from app.core.error_code import ErrorCode

logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


class GitHubAppError(RuntimeError):
    """A safe, user-facing GitHub API or installation access error."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
    ) -> None:
        self.error_code = error_code
        super().__init__(message)


class GitHubAppClient:
    """Mint short-lived installation tokens and read repository metadata."""

    def __init__(
        self,
        config: Settings | None = None,
        *,
        timeout_seconds: int = 15,
    ) -> None:
        self._settings = config or settings
        self._timeout_seconds = timeout_seconds
        self._token_cache: dict[int, tuple[str, datetime]] = {}
        self._cache_lock = Lock()

    def installation_token(self, installation_id: int) -> str:
        """Return a cached or newly minted token for one App installation."""

        if installation_id <= 0:
            raise GitHubAppError("GitHub installation is invalid.")

        now = datetime.now(UTC)
        with self._cache_lock:
            cached = self._token_cache.get(installation_id)
            if cached is not None and cached[1] > now + timedelta(minutes=2):
                return cached[0]

        app_jwt = self._create_app_jwt()
        payload = self._request_json(
            f"/app/installations/{installation_id}/access_tokens",
            method="POST",
            token=app_jwt,
            body={"permissions": {"contents": "read"}},
        )
        access_token = payload.get("token")
        expires_at_text = payload.get("expires_at")
        if not isinstance(access_token, str) or not isinstance(expires_at_text, str):
            raise GitHubAppError("GitHub did not return a valid installation token.")

        try:
            expires_at = datetime.fromisoformat(expires_at_text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GitHubAppError(
                "GitHub returned an invalid token expiry time."
            ) from exc

        with self._cache_lock:
            self._token_cache[installation_id] = (access_token, expires_at)
        return access_token

    def list_branches(
        self,
        owner: str,
        repository: str,
        *,
        installation_id: int | None = None,
    ) -> list[str]:
        """Return all branch names visible publicly or to an installation."""

        token = (
            self.installation_token(installation_id)
            if installation_id is not None
            else None
        )
        branch_names: list[str] = []
        page = 1
        while True:
            result = self._request_json(
                f"/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"
                f"/branches?per_page=100&page={page}",
                token=token,
            )
            if not isinstance(result, list):
                raise GitHubAppError("GitHub returned an invalid branch list.")

            for branch in result:
                name = branch.get("name") if isinstance(branch, dict) else None
                if isinstance(name, str):
                    branch_names.append(name)

            if len(result) < 100:
                break
            page += 1

        return branch_names

    def branch_commit_sha(
        self,
        owner: str,
        repository: str,
        branch_name: str,
        *,
        installation_id: int | None = None,
    ) -> str:
        """Return the latest commit SHA for one branch."""

        token = (
            self.installation_token(installation_id)
            if installation_id is not None
            else None
        )
        payload = self._request_json(
            f"/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"
            f"/branches/{quote(branch_name, safe='')}",
            token=token,
        )
        commit = payload.get("commit") if isinstance(payload, dict) else None
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str):
            raise GitHubAppError("GitHub did not return a commit SHA for this branch.")
        return sha

    def installation_belongs_to_app(self, installation_id: int) -> bool:
        """Check an installation ID against this GitHub App's identity."""

        app_id = self._settings.GITHUB_APP_ID
        if app_id is None:
            raise GitHubAppError(
                "GitHub App credentials are not configured on the server."
            )
        payload = self._request_json(
            f"/app/installations/{installation_id}",
            token=self._create_app_jwt(),
        )
        return isinstance(payload, dict) and str(payload.get("app_id")) == str(app_id)

    def _create_app_jwt(self) -> str:
        app_id = self._settings.GITHUB_APP_ID
        private_key = self._settings.GITHUB_APP_PRIVATE_KEY.get_secret_value()
        if app_id is None or not app_id.strip() or not app_id.strip().isdigit():
            raise GitHubAppError("GitHub App ID is missing or invalid.")
        if not private_key.strip():
            raise GitHubAppError(
                "GitHub App credentials are not configured on the server."
            )

        now = int(datetime.now(UTC).timestamp())
        try:
            return jwt.encode(
                {"iat": now - 30, "exp": now + 8 * 60, "iss": int(app_id)},
                private_key.replace("\\n", "\n"),
                algorithm="RS256",
            )
        except Exception as exc:
            logger.warning("Could not sign GitHub App JWT")
            raise GitHubAppError("GitHub App credentials could not be used.") from exc

    def _request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        token: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{GITHUB_API_BASE_URL}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise GitHubAppError(
                    "GitHub App authentication failed or lacks repository access.",
                    ErrorCode.FORBIDDEN,
                ) from exc
            if exc.code == 404:
                raise GitHubAppError(
                    "Repository was not found or is not accessible to this workspace's GitHub App.",
                    ErrorCode.RESOURCE_NOT_FOUND,
                ) from exc
            if exc.code == 429:
                raise GitHubAppError(
                    "GitHub API rate limit reached. Please retry later.",
                    ErrorCode.RATE_LIMIT_EXCEEDED,
                ) from exc
            if exc.code >= 500:
                raise GitHubAppError(
                    "GitHub is temporarily unavailable.",
                    ErrorCode.SYSTEM_ERROR,
                ) from exc
            raise GitHubAppError(
                f"GitHub API request failed with HTTP status {exc.code}.",
                ErrorCode.BAD_REQUEST,
            ) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise GitHubAppError("Could not connect to GitHub.") from exc


github_app_client = GitHubAppClient()
