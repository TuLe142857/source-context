"""Scan a local or public GitHub repository from the command line."""

import argparse
import json
from typing import Any

from app.core.config import get_settings
from app.schemas.repository import RepositorySnapshot
from app.repository_manager import RepositoryManager


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Prepare and scan a source repository.",
    )

    subparsers = parser.add_subparsers(
        dest="source_type",
        required=True,
    )

    local_parser = subparsers.add_parser(
        "local",
        help="Scan an existing local Git repository.",
    )
    local_parser.add_argument(
        "path",
        help="Path to the local repository or a subdirectory.",
    )

    github_parser = subparsers.add_parser(
        "github",
        help="Clone or reuse a public GitHub repository.",
    )
    github_parser.add_argument(
        "url",
        help="Public GitHub HTTPS repository URL.",
    )

    return parser


def snapshot_to_dict(
    snapshot: RepositorySnapshot,
) -> dict[str, Any]:
    """Convert a RepositorySnapshot into printable JSON."""

    return {
        "repository": {
            "repository_id": (snapshot.repository.repository_id),
            "source_type": (snapshot.repository.source_type.value),
            "acquisition_status": (snapshot.repository.acquisition_status.value),
            "name": snapshot.repository.name,
            "owner": snapshot.repository.owner,
            "local_path": str(
                snapshot.repository.local_path,
            ),
            "remote_url": (snapshot.repository.remote_url),
        },
        "git": {
            "branch": snapshot.git.branch,
            "commit_sha": snapshot.git.commit_sha,
            "remote_url": snapshot.git.remote_url,
        },
        "statistics": {
            "discovered_file_count": (snapshot.statistics.discovered_file_count),
            "included_file_count": (snapshot.statistics.included_file_count),
            "ignored_file_count": (snapshot.statistics.ignored_file_count),
            "pruned_directory_count": (snapshot.statistics.pruned_directory_count),
            "unsupported_file_count": (snapshot.statistics.unsupported_file_count),
            "oversized_file_count": (snapshot.statistics.oversized_file_count),
            "binary_file_count": (snapshot.statistics.binary_file_count),
            "symlink_file_count": (snapshot.statistics.symlink_file_count),
            "inaccessible_file_count": (snapshot.statistics.inaccessible_file_count),
        },
        "files": [
            {
                "relative_path": (source_file.relative_path.as_posix()),
                "language": (source_file.language.value),
                "size_bytes": (source_file.size_bytes),
                "content_hash": (source_file.content_hash),
            }
            for source_file in snapshot.files
        ],
    }


def main() -> None:
    """Execute a repository scan."""

    arguments = build_parser().parse_args()

    manager = RepositoryManager.from_settings(
        get_settings(),
    )

    if arguments.source_type == "local":
        snapshot = manager.scan_local(
            arguments.path,
        )
    else:
        snapshot = manager.scan_github_public(
            arguments.url,
        )

    print(
        json.dumps(
            snapshot_to_dict(snapshot),
            indent=2,
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
