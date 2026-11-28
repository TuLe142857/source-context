"""Utility functions for profile extractor."""

import logging
from pathlib import Path

from app.repository_manager_v2.profile_extractor.catalog.common import (
    DIRECTORY_ROLES,
    IGNORE_DIRS,
)

logger = logging.getLogger(__name__)


def scan_shallow_directory_map(dir_path: Path, max_depth: int = 2) -> dict[str, str]:
    """Scans directory structure up to max_depth, skipping cache and build dirs.

    Args:
        dir_path (Path): Root directory on local disk.
        max_depth (int, optional): Maximum depth to traverse. Defaults to 2.

    Returns:
        dict[str, str]: Mapping of relative path to directory role description.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return {}

    directory_map: dict[str, str] = {}

    def _walk(current: Path, current_depth: int) -> None:
        if current_depth > max_depth:
            return

        try:
            for entry in sorted(current.iterdir()):
                if not entry.is_dir():
                    continue

                dir_name = entry.name
                if dir_name in IGNORE_DIRS or dir_name.startswith("."):
                    continue

                rel_path = str(entry.relative_to(dir_path))
                role = DIRECTORY_ROLES.get(
                    rel_path, DIRECTORY_ROLES.get(dir_name, "Directory")
                )
                directory_map[rel_path] = role

                if current_depth < max_depth:
                    _walk(entry, current_depth + 1)
        except (PermissionError, OSError) as exc:
            logger.debug("Cannot access directory %s: %s", current, exc)

    _walk(dir_path, 1)
    return directory_map
