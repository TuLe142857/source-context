"""Python language profile extractor.

Inspects Python projects by analyzing pyproject.toml, requirements.txt, Pipfile,
detecting frameworks, test runners, linters, and architectural entrypoints.
"""

from collections.abc import Sequence
import logging
import re
import tomllib

from app.repository_manager_v2.profile_extractor.catalog.python_rules import (
    PYTHON_PACKAGE_CATALOG,
    PythonPackageRule,
)
from app.repository_manager_v2.profile_extractor.extractors.base import (
    BaseLanguageExtractor,
)
from app.repository_manager_v2.profile_extractor.models import (
    CodingConventionsInfo,
    DevCommandsInfo,
    MetricsInfo,
    RepoProfileResult,
    TechStackInfo,
)
from app.repository_manager_v2.profile_extractor.providers.base import (
    SourceFileProvider,
)

logger = logging.getLogger(__name__)


class PythonProfileExtractor(BaseLanguageExtractor):
    """Extractor for Python ecosystem repositories."""

    MANIFEST_FILES: tuple[str, ...] = (
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
        "setup.cfg",
    )

    COMMON_ENTRYPOINTS: tuple[str, ...] = (
        "main.py",
        "app/main.py",
        "src/main.py",
        "manage.py",
        "app.py",
        "server.py",
        "wsgi.py",
        "asgi.py",
        "worker.py",
        "app/worker.py",
    )

    DIRECTORY_HINTS: tuple[tuple[str, str], ...] = (
        ("app/api", "API Routers and Controllers"),
        ("src/api", "API Routers and Controllers"),
        ("app/services", "Core Business Logic and Services"),
        ("src/services", "Core Business Logic and Services"),
        ("app/model", "Database ORM Models"),
        ("app/models", "Database ORM Models"),
        ("src/models", "Database ORM Models"),
        ("app/schemas", "Request/Response Pydantic Schemas"),
        ("src/schemas", "Request/Response Schemas"),
        ("tests", "Automated Test Suite"),
        ("alembic", "Database Migrations (Alembic)"),
        ("migrations", "Database Migrations"),
    )

    @property
    def language_name(self) -> str:
        """Returns the primary language name."""
        return "python"

    def can_handle(self, provider: SourceFileProvider) -> bool:
        """Checks if any Python manifest or Python source files exist."""
        for manifest in self.MANIFEST_FILES:
            if provider.exists(manifest):
                return True
        # Also check for common lock files
        if provider.exists("uv.lock") or provider.exists("poetry.lock"):
            return True
        return False

    def extract(self, provider: SourceFileProvider) -> RepoProfileResult:
        """Extracts technical profile from Python project manifests and files."""
        tech_stack = TechStackInfo(language=self.language_name)
        dev_commands = DevCommandsInfo()
        coding_conventions = CodingConventionsInfo(naming="snake_case")
        metrics = MetricsInfo()

        detected_manifests: list[str] = []
        parsed_dependencies: set[str] = set()

        # 1. Parse pyproject.toml if present
        if provider.exists("pyproject.toml"):
            detected_manifests.append("pyproject.toml")
            self._parse_pyproject(
                provider,
                tech_stack,
                dev_commands,
                coding_conventions,
                parsed_dependencies,
            )

        # 2. Parse requirements.txt if present
        if provider.exists("requirements.txt"):
            detected_manifests.append("requirements.txt")
            self._parse_requirements(provider, "requirements.txt", parsed_dependencies)

        # 3. Check lock files for package manager resolution
        if provider.exists("uv.lock"):
            tech_stack.package_manager = "uv"
            detected_manifests.append("uv.lock")
        elif provider.exists("poetry.lock"):
            tech_stack.package_manager = "poetry"
            detected_manifests.append("poetry.lock")
        elif provider.exists("Pipfile.lock") or provider.exists("Pipfile"):
            tech_stack.package_manager = "pipenv"
            if provider.exists("Pipfile"):
                detected_manifests.append("Pipfile")
        elif not tech_stack.package_manager:
            tech_stack.package_manager = (
                "pip" if provider.exists("requirements.txt") else None
            )

        # 4. Map parsed dependencies using the catalog
        self._apply_catalog(
            parsed_dependencies, tech_stack, dev_commands, coding_conventions
        )

        # 5. Detect entrypoints
        entrypoints: list[str] = [
            ep for ep in self.COMMON_ENTRYPOINTS if provider.is_file(ep)
        ]

        # 6. Map directory responsibilities
        directory_map: dict[str, str] = {}
        for dir_path, role in self.DIRECTORY_HINTS:
            if provider.is_dir(dir_path):
                directory_map[dir_path] = role

        # 7. Check README
        for name in provider.list_dir(""):
            if name.lower().startswith("readme"):
                metrics.has_readme = True
                metrics.readme_file = name
                break

        metrics.detected_manifests = detected_manifests

        # 8. Determine project type
        project_type = self._determine_project_type(tech_stack, entrypoints, provider)

        return RepoProfileResult(
            primary_language=self.language_name,
            project_type=project_type,
            tech_stack=tech_stack,
            key_entrypoints=entrypoints,
            directory_map=directory_map,
            dev_commands=dev_commands,
            coding_conventions=coding_conventions,
            metrics=metrics,
        )

    def _parse_pyproject(
        self,
        provider: SourceFileProvider,
        tech_stack: TechStackInfo,
        dev_commands: DevCommandsInfo,
        conventions: CodingConventionsInfo,
        collected_deps: set[str],
    ) -> None:
        """Parses pyproject.toml configuration and dependencies."""
        content = provider.read_text("pyproject.toml")
        if not content:
            return

        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError as exc:
            logger.warning("Failed to parse pyproject.toml: %s", exc)
            return

        # Check Python version requirements
        project_table = data.get("project", {})
        if "requires-python" in project_table:
            tech_stack.runtime_version = str(project_table["requires-python"])

        # Dependencies from PEP 621 [project.dependencies]
        deps: Sequence[str] = project_table.get("dependencies", [])
        for dep in deps:
            pkg = self._clean_package_name(dep)
            if pkg:
                collected_deps.add(pkg)

        # Optional / Dev dependencies from PEP 621 [project.optional-dependencies]
        opt_deps = project_table.get("optional-dependencies", {})
        if isinstance(opt_deps, dict):
            for group in opt_deps.values():
                if isinstance(group, list):
                    for dep in group:
                        pkg = self._clean_package_name(str(dep))
                        if pkg:
                            collected_deps.add(pkg)

        # Poetry dependencies [tool.poetry.dependencies]
        tool_table = data.get("tool", {})
        poetry_table = tool_table.get("poetry", {})
        if poetry_table:
            tech_stack.package_manager = tech_stack.package_manager or "poetry"
            p_deps = poetry_table.get("dependencies", {})
            if isinstance(p_deps, dict):
                for dep in p_deps:
                    if dep.lower() != "python":
                        collected_deps.add(dep.lower())
            p_dev_deps = poetry_table.get("group", {})
            if isinstance(p_dev_deps, dict):
                for group in p_dev_deps.values():
                    if isinstance(group, dict):
                        for dep in group.get("dependencies", {}):
                            collected_deps.add(dep.lower())

        # Tool configs
        if "ruff" in tool_table:
            conventions.linter = "ruff"
            conventions.formatter = "ruff"
            dev_commands.lint = dev_commands.lint or "ruff check ."
            dev_commands.format = dev_commands.format or "ruff format ."
        if "mypy" in tool_table:
            conventions.strict_typing = True
            dev_commands.lint = dev_commands.lint or "mypy ."
        if "pytest" in tool_table:
            dev_commands.test = dev_commands.test or "pytest"

    def _parse_requirements(
        self,
        provider: SourceFileProvider,
        file_path: str,
        collected_deps: set[str],
    ) -> None:
        """Parses requirements.txt format files."""
        content = provider.read_text(file_path)
        if not content:
            return

        for line in content.splitlines():
            clean = line.strip()
            if not clean or clean.startswith(("#", "-r", "-i", "-f")):
                continue
            pkg = self._clean_package_name(clean)
            if pkg:
                collected_deps.add(pkg)

    def _apply_catalog(
        self,
        dependencies: set[str],
        tech_stack: TechStackInfo,
        dev_commands: DevCommandsInfo,
        conventions: CodingConventionsInfo,
    ) -> None:
        """Matches extracted packages with the declarative rule catalog."""
        for pkg in sorted(dependencies):
            rule: PythonPackageRule | None = PYTHON_PACKAGE_CATALOG.get(pkg)
            if not rule:
                tech_stack.extra_packages.append(pkg)
                continue

            name = rule.get("display_name", pkg)
            cat = rule.get("category", "")

            if cat == "framework" and name not in tech_stack.frameworks:
                tech_stack.frameworks.append(name)
            elif cat == "orm" and name not in tech_stack.orm:
                tech_stack.orm.append(name)
            elif cat == "database" and name not in tech_stack.databases:
                tech_stack.databases.append(name)
            elif cat == "task_queue" and name not in tech_stack.task_queues:
                tech_stack.task_queues.append(name)
            elif cat == "linter" and name not in tech_stack.linters:
                tech_stack.linters.append(name)
            elif cat == "test_framework" and name not in tech_stack.test_frameworks:
                tech_stack.test_frameworks.append(name)

            # Apply default commands if not set, giving web frameworks precedence for run command
            if "command_run" in rule:
                if not dev_commands.run or cat == "framework":
                    dev_commands.run = rule["command_run"]
            if "command_test" in rule and not dev_commands.test:
                dev_commands.test = rule["command_test"]
            if "command_lint" in rule and not dev_commands.lint:
                dev_commands.lint = rule["command_lint"]
            if "command_format" in rule and not dev_commands.format:
                dev_commands.format = rule["command_format"]

            # Apply conventions
            if "convention_linter" in rule and not conventions.linter:
                conventions.linter = rule["convention_linter"]
            if "convention_formatter" in rule and not conventions.formatter:
                conventions.formatter = rule["convention_formatter"]
            if rule.get("convention_strict_typing"):
                conventions.strict_typing = True

    def _determine_project_type(
        self,
        tech_stack: TechStackInfo,
        entrypoints: list[str],
        provider: SourceFileProvider,
    ) -> str:
        """Determines high-level project type."""
        if any("FastAPI" in f for f in tech_stack.frameworks):
            return "fastapi_api"
        if any("Django" in f for f in tech_stack.frameworks):
            return "django_app"
        if any("Flask" in f for f in tech_stack.frameworks):
            return "flask_app"
        if provider.exists("manage.py"):
            return "django_app"
        if (
            provider.exists("setup.py")
            and not entrypoints
            and not tech_stack.frameworks
        ):
            return "python_library"
        return "python_service"

    @staticmethod
    def _clean_package_name(raw_name: str) -> str | None:
        """Extracts the normalized canonical package name from a dependency specification."""
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)", raw_name.strip())
        if match:
            return match.group(1).lower().replace("_", "-")
        return None
