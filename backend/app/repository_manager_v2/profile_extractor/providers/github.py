"""GitHub API implementation of SourceFileProvider.

Enables Zero-Clone repository inspection by querying GitHub's Git Trees
and Contents APIs without downloading the repository to disk.
"""

import base64
from collections.abc import Sequence
import fnmatch
import logging
from typing import Any
from urllib.parse import quote

import requests

from app.repository_manager_v2.exceptions import GitHubAppApiError

logger = logging.getLogger(__name__)


class GitHubApiSourceProvider:
    """Source file provider backed by GitHub REST APIs (Zero-Clone)."""

    def __init__(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        token: str | None = None,
        timeout: int = 20,
    ) -> None:
        """Initializes the GitHubApiSourceProvider.

        Args:
            owner (str): Repository owner (user or organization).
            repo (str): Repository name.
            branch (str, optional): Target branch or commit SHA. Defaults to "main".
            token (str | None, optional): GitHub access token. Defaults to None.
            timeout (int, optional): Timeout in seconds for HTTP requests. Defaults to 20.
        """
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.token = token
        self.timeout = timeout

        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Source-Context-Backend",
        }
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

        self._tree_loaded: bool = False
        self._blobs: dict[str, dict[str, Any]] = {}
        self._dirs: set[str] = set()
        self._content_cache: dict[str, str] = {}

    def _ensure_tree(self) -> None:
        """Fetches the entire recursive Git tree once and indexes paths."""
        if self._tree_loaded:
            return

        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{self.branch}?recursive=1"
        try:
            response = requests.get(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            items = data.get("tree", [])

            for item in items:
                path = item.get("path", "").strip("/")
                item_type = item.get("type", "")
                if item_type == "blob":
                    self._blobs[path] = item
                elif item_type == "tree":
                    self._dirs.add(path)

                # Ensure intermediate directory parents are recorded
                parts = path.split("/")
                for i in range(1, len(parts)):
                    self._dirs.add("/".join(parts[:i]))

            self._tree_loaded = True
            logger.info(
                "Loaded GitHub tree for %s/%s@%s: %d files, %d directories",
                self.owner,
                self.repo,
                self.branch,
                len(self._blobs),
                len(self._dirs),
            )
        except requests.RequestException as exc:
            status_code = getattr(exc.response, "status_code", None)
            logger.warning(
                "Failed to fetch Git tree for %s/%s@%s: %s",
                self.owner,
                self.repo,
                self.branch,
                exc,
            )
            self._tree_loaded = True
            if status_code in (401, 403, 404):
                raise GitHubAppApiError(
                    f"GitHub API error fetching tree for {self.owner}/{self.repo}@{self.branch}: {exc}",
                    status_code=status_code,
                ) from exc

    def exists(self, relative_path: str) -> bool:
        """Checks if a file or directory exists at the relative path."""
        self._ensure_tree()
        clean = relative_path.strip("/")
        return clean in self._blobs or clean in self._dirs

    def is_file(self, relative_path: str) -> bool:
        """Checks if the path is an existing regular file (blob)."""
        self._ensure_tree()
        clean = relative_path.strip("/")
        return clean in self._blobs

    def is_dir(self, relative_path: str) -> bool:
        """Checks if the path is an existing directory."""
        self._ensure_tree()
        clean = relative_path.strip("/")
        if not clean:
            return True
        return clean in self._dirs

    def read_text(self, relative_path: str) -> str | None:
        """Reads file content as a UTF-8 string via GitHub Contents API."""
        self._ensure_tree()
        clean = relative_path.strip("/")
        if clean not in self._blobs:
            return None

        if clean in self._content_cache:
            return self._content_cache[clean]

        quoted_path = quote(clean, safe="/")
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{quoted_path}?ref={self.branch}"
        try:
            response = requests.get(url, headers=self._headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            encoded_content = data.get("content", "")
            encoding = data.get("encoding", "")

            if encoding == "base64" and encoded_content:
                text = base64.b64decode(encoded_content).decode(
                    "utf-8", errors="replace"
                )
                self._content_cache[clean] = text
                return text

            # Raw text fallback
            return None
        except requests.RequestException as exc:
            logger.warning(
                "Failed to fetch content for %s at %s/%s: %s",
                clean,
                self.owner,
                self.repo,
                exc,
            )
            return None

    def list_dir(self, relative_path: str = "") -> Sequence[str]:
        """Lists file and directory names directly inside a directory."""
        self._ensure_tree()
        clean = relative_path.strip("/")
        depth = 0 if not clean else len(clean.split("/"))
        prefix = f"{clean}/" if clean else ""

        entries: set[str] = set()

        for path in self._blobs:
            if not prefix or path.startswith(prefix):
                parts = path.split("/")
                if len(parts) == depth + 1:
                    entries.add(parts[depth])

        for path in self._dirs:
            if not prefix or path.startswith(prefix):
                parts = path.split("/")
                if len(parts) == depth + 1:
                    entries.add(parts[depth])

        return sorted(entries)

    def find_files(self, pattern: str, max_depth: int = 3) -> Sequence[str]:
        """Finds relative file paths matching a simple name pattern up to a maximum depth."""
        self._ensure_tree()
        matches: list[str] = []

        for path in self._blobs:
            parts = path.split("/")
            if len(parts) <= max_depth:
                filename = parts[-1]
                if fnmatch.fnmatch(filename, pattern):
                    matches.append(path)

        return sorted(matches)
