"""Sub-repository technical profile dispatcher using registered language extractors."""

import logging
from pathlib import Path

from app.repository_manager_v2.profile_extractor.extractors.registry import (
    SubprojectExtractorRegistry,
    get_default_subproject_registry,
)
from app.repository_manager_v2.profile_extractor.models import SubrepoProfileResult
from app.repository_manager_v2.profile_extractor.utils import scan_shallow_directory_map

logger = logging.getLogger(__name__)


def extract_subproject_profile(
    local_dir: Path,
    language: str,
    name: str = "",
    root_dir: str = ".",
    registry: SubprojectExtractorRegistry | None = None,
) -> SubrepoProfileResult:
    """Dispatches profile extraction based on project's configured language.

    Args:
        local_dir (Path): Absolute directory of the subproject.
        language (str): Language configured for the project (e.g. python, typescript).
        name (str, optional): Subproject name. Defaults to "".
        root_dir (str, optional): Relative root dir. Defaults to ".".
        registry (SubprojectExtractorRegistry | None, optional): Custom registry. Defaults to None.

    Returns:
        SubrepoProfileResult: Extracted sub-repository technical profile.
    """
    reg = registry or get_default_subproject_registry()
    extractor = reg.get(language)

    if extractor is not None:
        return extractor.extract(
            local_dir=local_dir,
            name=name,
            root_dir=root_dir,
            language=language,
        )

    # Generic fallback if no specific extractor is registered for the language
    logger.info(
        "No specific extractor registered for language '%s'. Using generic fallback.",
        language,
    )
    directory_map = scan_shallow_directory_map(local_dir, max_depth=2)
    return SubrepoProfileResult(
        name=name or local_dir.name,
        root_dir=root_dir,
        language=language.lower(),
        project_type="generic_project",
        directory_map=directory_map,
    )
