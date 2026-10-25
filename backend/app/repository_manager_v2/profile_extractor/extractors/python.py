"""Python sub-project extractor using catalog dictionary configuration."""

import logging
from pathlib import Path
import re
import tomllib

from app.repository_manager_v2.profile_extractor.catalog.python import PYTHON_CATALOG
from app.repository_manager_v2.profile_extractor.extractors.base import (
    BaseSubprojectExtractor,
)
from app.repository_manager_v2.profile_extractor.models import SubrepoProfileResult
from app.repository_manager_v2.profile_extractor.utils import scan_shallow_directory_map

logger = logging.getLogger(__name__)


class PythonSubprojectExtractor(BaseSubprojectExtractor):
    """Extractor for Python sub-projects based on PYTHON_CATALOG configuration."""

    @property
    def supported_languages(self) -> list[str]:
        """Returns list of supported languages."""
        return ["python"]

    def extract(
        self,
        local_dir: Path,
        name: str,
        root_dir: str,
        language: str | None = None,
    ) -> SubrepoProfileResult:
        """Extracts technical profile for a Python sub-project from local disk."""
        detected_frameworks: list[str] = []
        collected_deps: set[str] = set()
        key_entrypoints: list[str] = []
        package_manager: str | None = None
        runtime_version: str | None = None
        project_type = "python_app"

        # 1. Detect Package Manager from Catalog
        pm_rules: dict[str, str] = PYTHON_CATALOG.get("package_managers", {})
        for lock_file, pm_name in pm_rules.items():
            if (local_dir / lock_file).exists():
                package_manager = pm_name
                break

        # 2. Parse pyproject.toml if present
        pyproject_file = local_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                with open(pyproject_file, "rb") as f_pyproject:
                    data = tomllib.load(f_pyproject)

                project_meta = data.get("project", {})
                if "requires-python" in project_meta:
                    runtime_version = str(project_meta["requires-python"])

                # Dependencies
                for dep in project_meta.get("dependencies", []):
                    match = re.split(r"[><=~!;]", str(dep).strip())
                    if match:
                        collected_deps.add(match[0].strip().lower())

                # Scripts entrypoints
                scripts = project_meta.get("scripts", {})
                if isinstance(scripts, dict):
                    for script_name, target in scripts.items():
                        key_entrypoints.append(f"{script_name} -> {target}")

                # Poetry tool dependencies
                poetry_deps = (
                    data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                )
                if isinstance(poetry_deps, dict):
                    if not package_manager:
                        package_manager = "poetry"
                    for dep_name in poetry_deps:
                        if dep_name.lower() != "python":
                            collected_deps.add(dep_name.lower())
            except Exception as exc:
                logger.warning(
                    "Failed parsing pyproject.toml at %s: %s", pyproject_file, exc
                )

        # 3. Parse requirements.txt if present
        req_file = local_dir / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    match = re.split(r"[><=~!;]", line)
                    if match:
                        collected_deps.add(match[0].strip().lower())
            except Exception as exc:
                logger.warning(
                    "Failed reading requirements.txt at %s: %s", req_file, exc
                )

        # 4. Match with Catalog Frameworks
        frameworks_catalog: dict[str, dict[str, str | None]] = PYTHON_CATALOG.get(
            "frameworks", {}
        )
        inferred_type: str | None = None
        for dep in sorted(collected_deps):
            if dep in frameworks_catalog:
                entry = frameworks_catalog[dep]
                fw_name = entry.get("name")
                fw_type = entry.get("type")
                if fw_name and fw_name not in detected_frameworks:
                    detected_frameworks.append(fw_name)
                if fw_type and not inferred_type:
                    inferred_type = fw_type

        if inferred_type:
            project_type = inferred_type

        # 5. Check candidate entrypoint files from Catalog
        candidate_entrypoints: list[str] = PYTHON_CATALOG.get("entrypoint_files", [])
        for candidate in candidate_entrypoints:
            if (local_dir / candidate).exists():
                entry_path = f"{root_dir}/{candidate}".lstrip("./")
                if entry_path not in key_entrypoints:
                    key_entrypoints.append(entry_path)

        # 6. Check scripts directory
        scripts_dir = local_dir / "scripts"
        if scripts_dir.exists() and scripts_dir.is_dir():
            for script_file in sorted(scripts_dir.glob("*.py")):
                rel_f = str(script_file.relative_to(local_dir))
                entry_path = f"{root_dir}/{rel_f}".lstrip("./")
                if entry_path not in key_entrypoints:
                    key_entrypoints.append(entry_path)

        # 7. Shallow directory map
        directory_map = scan_shallow_directory_map(local_dir, max_depth=2)

        return SubrepoProfileResult(
            name=name or local_dir.name,
            root_dir=root_dir,
            language="python",
            project_type=project_type,
            frameworks=detected_frameworks,
            tech_stack={
                "language": "python",
                "runtime_version": runtime_version,
                "package_manager": package_manager or "pip",
                "dependencies": sorted(collected_deps),
            },
            key_entrypoints=key_entrypoints,
            directory_map=directory_map,
        )
