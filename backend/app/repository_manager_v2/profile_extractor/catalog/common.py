"""Common catalog rules, directory ignore sets, and architectural role mappings."""

from typing import Final

IGNORE_DIRS: Final[set[str]] = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".idea",
    ".vscode",
    ".tox",
}

DIRECTORY_ROLES: Final[dict[str, str]] = {
    "src": "Application Source Code Root",
    "src/components": "UI Components",
    "src/pages": "Page Views / Routes",
    "src/app": "Application Router Root",
    "src/api": "API Clients & Routes",
    "src/services": "Business Logic Services",
    "src/models": "Data Models & Schemas",
    "src/utils": "Utility Functions",
    "scripts": "Automation & Utility Scripts",
    "tests": "Test Suite",
    "test": "Test Suite",
    "docs": "Documentation",
    "public": "Static Assets",
    "assets": "Static Assets",
}
