"""Catalog package for rule-based dependency categorization."""

from app.repository_manager_v2.profile_extractor.catalog.python_rules import (
    PYTHON_PACKAGE_CATALOG,
    PythonPackageRule,
)

__all__ = ["PYTHON_PACKAGE_CATALOG", "PythonPackageRule"]
