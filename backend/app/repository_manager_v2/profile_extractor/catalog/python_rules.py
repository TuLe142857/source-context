"""Rule catalog for Python dependencies, frameworks, and tools.

This module provides declarative mapping between known Python package names
and their architectural roles, default development commands, and conventions.
"""

from typing import TypedDict


class PythonPackageRule(TypedDict, total=False):
    """Metadata rule specification for a recognized Python package."""

    category: str
    display_name: str
    command_run: str
    command_test: str
    command_lint: str
    command_format: str
    convention_linter: str
    convention_formatter: str
    convention_strict_typing: bool


PYTHON_PACKAGE_CATALOG: dict[str, PythonPackageRule] = {
    # Web Frameworks
    "fastapi": {
        "category": "framework",
        "display_name": "FastAPI",
        "command_run": "uvicorn app.main:app --reload",
    },
    "django": {
        "category": "framework",
        "display_name": "Django",
        "command_run": "python manage.py runserver",
        "command_test": "python manage.py test",
    },
    "flask": {
        "category": "framework",
        "display_name": "Flask",
        "command_run": "flask run",
    },
    "starlette": {
        "category": "framework",
        "display_name": "Starlette",
    },
    "sanic": {
        "category": "framework",
        "display_name": "Sanic",
        "command_run": "sanic server:app",
    },
    "tornado": {
        "category": "framework",
        "display_name": "Tornado",
    },
    # ORM & Databases
    "sqlalchemy": {
        "category": "orm",
        "display_name": "SQLAlchemy",
    },
    "sqlmodel": {
        "category": "orm",
        "display_name": "SQLModel",
    },
    "tortoise-orm": {
        "category": "orm",
        "display_name": "Tortoise ORM",
    },
    "peewee": {
        "category": "orm",
        "display_name": "Peewee",
    },
    "alembic": {
        "category": "database",
        "display_name": "Alembic (Migrations)",
    },
    "asyncpg": {
        "category": "database",
        "display_name": "PostgreSQL (asyncpg)",
    },
    "psycopg2": {
        "category": "database",
        "display_name": "PostgreSQL (psycopg2)",
    },
    "psycopg": {
        "category": "database",
        "display_name": "PostgreSQL (psycopg3)",
    },
    "redis": {
        "category": "database",
        "display_name": "Redis",
    },
    "pymongo": {
        "category": "database",
        "display_name": "MongoDB (PyMongo)",
    },
    "motor": {
        "category": "database",
        "display_name": "MongoDB (Motor)",
    },
    # Asynchronous Task Queues
    "celery": {
        "category": "task_queue",
        "display_name": "Celery",
        "command_run": "celery -A app.worker worker --loglevel=info",
    },
    "arq": {
        "category": "task_queue",
        "display_name": "Arq",
    },
    "rq": {
        "category": "task_queue",
        "display_name": "RQ (Redis Queue)",
    },
    # Testing
    "pytest": {
        "category": "test_framework",
        "display_name": "pytest",
        "command_test": "pytest",
    },
    "pytest-asyncio": {
        "category": "test_framework",
        "display_name": "pytest-asyncio",
    },
    "unittest": {
        "category": "test_framework",
        "display_name": "unittest",
        "command_test": "python -m unittest",
    },
    # Linters & Formatters & Type Checkers
    "ruff": {
        "category": "linter",
        "display_name": "Ruff",
        "command_lint": "ruff check .",
        "command_format": "ruff format .",
        "convention_linter": "ruff",
        "convention_formatter": "ruff",
    },
    "black": {
        "category": "linter",
        "display_name": "Black",
        "command_format": "black .",
        "convention_formatter": "black",
    },
    "flake8": {
        "category": "linter",
        "display_name": "Flake8",
        "command_lint": "flake8 .",
        "convention_linter": "flake8",
    },
    "mypy": {
        "category": "linter",
        "display_name": "Mypy",
        "command_lint": "mypy .",
        "convention_strict_typing": True,
    },
    "pylint": {
        "category": "linter",
        "display_name": "Pylint",
        "command_lint": "pylint app",
    },
}
