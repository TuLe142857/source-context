"""JavaScript and TypeScript sub-project extractor using catalog dictionary configuration."""

import json
import logging
from pathlib import Path

from app.repository_manager_v2.profile_extractor.catalog.javascript import (
    JAVASCRIPT_CATALOG,
)
from app.repository_manager_v2.profile_extractor.extractors.base import (
    BaseSubprojectExtractor,
)
from app.repository_manager_v2.profile_extractor.models import SubrepoProfileResult
from app.repository_manager_v2.profile_extractor.utils import scan_shallow_directory_map

logger = logging.getLogger(__name__)


class JavaScriptSubprojectExtractor(BaseSubprojectExtractor):
    """Extractor for JavaScript and TypeScript sub-projects based on JAVASCRIPT_CATALOG."""

    @property
    def supported_languages(self) -> list[str]:
        """Returns list of supported languages."""
        return ["javascript", "typescript"]

    def extract(
        self,
        local_dir: Path,
        name: str,
        root_dir: str,
        language: str | None = None,
    ) -> SubrepoProfileResult:
        """Extracts technical profile for a JS/TS sub-project from local disk."""
        detected_frameworks: list[str] = []
        collected_deps: set[str] = set()
        key_entrypoints: list[str] = []
        package_manager: str | None = None
        project_type = "frontend_app"

        # Determine effective language (respect user's choice if provided)
        lang: str
        if language and language.lower() in ("typescript", "javascript"):
            lang = language.lower()
        elif (local_dir / "tsconfig.json").exists():
            lang = "typescript"
        else:
            lang = "javascript"

        # 1. Detect Package Manager from Catalog
        pm_rules: dict[str, str] = JAVASCRIPT_CATALOG.get("package_managers", {})
        for lock_file, pm_name in pm_rules.items():
            if (local_dir / lock_file).exists():
                package_manager = pm_name
                break

        # 2. Parse package.json
        pkg_file = local_dir / "package.json"
        if pkg_file.exists():
            try:
                with open(pkg_file, "r", encoding="utf-8") as f_pkg:
                    pkg_data = json.load(f_pkg)

                deps = pkg_data.get("dependencies", {})
                dev_deps = pkg_data.get("devDependencies", {})
                if isinstance(deps, dict):
                    collected_deps.update(k.lower() for k in deps.keys())
                if isinstance(dev_deps, dict):
                    collected_deps.update(k.lower() for k in dev_deps.keys())

                # If typescript is detected in dependencies and no explicit lang was provided
                if "typescript" in collected_deps and not language:
                    lang = "typescript"

                # Check scripts
                scripts = pkg_data.get("scripts", {})
                script_keys: list[str] = JAVASCRIPT_CATALOG.get(
                    "script_keys", ["dev", "start", "build"]
                )
                if isinstance(scripts, dict):
                    for script_key, cmd in scripts.items():
                        if script_key in script_keys:
                            key_entrypoints.append(f"npm run {script_key} ({cmd})")
            except Exception as exc:
                logger.warning("Failed parsing package.json at %s: %s", pkg_file, exc)

        # 3. Match with Catalog Frameworks
        frameworks_catalog: dict[str, dict[str, str | None]] = JAVASCRIPT_CATALOG.get(
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

        # 4. Check candidate entrypoints from Catalog
        candidate_entrypoints: list[str] = JAVASCRIPT_CATALOG.get(
            "entrypoint_files", []
        )
        for candidate in candidate_entrypoints:
            if (local_dir / candidate).exists():
                entry_path = f"{root_dir}/{candidate}".lstrip("./")
                if entry_path not in key_entrypoints:
                    key_entrypoints.append(entry_path)

        # 5. Shallow directory map
        directory_map = scan_shallow_directory_map(local_dir, max_depth=2)

        return SubrepoProfileResult(
            name=name or local_dir.name,
            root_dir=root_dir,
            language=lang,
            project_type=project_type,
            frameworks=detected_frameworks,
            tech_stack={
                "language": lang,
                "package_manager": package_manager or "npm",
                "dependencies": sorted(collected_deps),
            },
            key_entrypoints=key_entrypoints,
            directory_map=directory_map,
        )
