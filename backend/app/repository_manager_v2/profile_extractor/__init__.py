"""Profile extractor package for repository and sub-repository technical profiling."""

from app.repository_manager_v2.profile_extractor.catalog import (
    DIRECTORY_ROLES,
    IGNORE_DIRS,
    JAVASCRIPT_CATALOG,
    PYTHON_CATALOG,
)
from app.repository_manager_v2.profile_extractor.extractor import (
    extract_subproject_profile,
)
from app.repository_manager_v2.profile_extractor.extractors import (
    BaseSubprojectExtractor,
    JavaScriptSubprojectExtractor,
    PythonSubprojectExtractor,
    SubprojectExtractorRegistry,
    get_default_subproject_registry,
)
from app.repository_manager_v2.profile_extractor.models import (
    RepoProfileResult,
    SubrepoProfileResult,
)
from app.repository_manager_v2.profile_extractor.service import (
    RepoProfileService,
)
from app.repository_manager_v2.profile_extractor.utils import (
    scan_shallow_directory_map,
)

__all__ = [
    "BaseSubprojectExtractor",
    "DIRECTORY_ROLES",
    "IGNORE_DIRS",
    "JAVASCRIPT_CATALOG",
    "JavaScriptSubprojectExtractor",
    "PYTHON_CATALOG",
    "PythonSubprojectExtractor",
    "RepoProfileResult",
    "RepoProfileService",
    "SubprojectExtractorRegistry",
    "SubrepoProfileResult",
    "extract_subproject_profile",
    "get_default_subproject_registry",
    "scan_shallow_directory_map",
]
