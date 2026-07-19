"""Ignore rules used by the local repository scanner."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pathspec import GitIgnoreSpec

DEFAULT_IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".coverage",
        ".next",
        ".nuxt",
        ".output",
        ".turbo",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
    },
)


@dataclass(frozen=True, slots=True)
class IgnoreRules:
    """Root-level ignore rules for one repository."""

    gitignore_spec: GitIgnoreSpec

    @classmethod
    def from_repository(
        cls,
        repository_root: Path,
    ) -> "IgnoreRules":
        """Load root `.gitignore` patterns."""

        gitignore_path = repository_root / ".gitignore"

        if not gitignore_path.is_file():
            return cls(
                gitignore_spec=GitIgnoreSpec.from_lines([]),
            )

        patterns = gitignore_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        return cls(
            gitignore_spec=GitIgnoreSpec.from_lines(patterns),
        )

    def should_prune_directory(
        self,
        *,
        directory_name: str,
        directory_path: Path,
        relative_path: PurePosixPath,
    ) -> bool:
        """Return whether directory traversal should stop."""

        if directory_name in DEFAULT_IGNORED_DIRECTORY_NAMES:
            return True

        if directory_path.is_symlink():
            return True

        return self.matches_gitignore(
            relative_path,
            is_directory=True,
        )

    def matches_gitignore(
        self,
        relative_path: PurePosixPath,
        *,
        is_directory: bool = False,
    ) -> bool:
        """Return whether a repository-relative path is ignored."""

        normalized_path = relative_path.as_posix()

        if is_directory:
            normalized_path = f"{normalized_path}/"

        return self.gitignore_spec.match_file(
            normalized_path,
        )
