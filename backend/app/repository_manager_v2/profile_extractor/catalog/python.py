"""Python language catalog defining frameworks, libraries, manifests, and entrypoint patterns."""

from typing import Any

PYTHON_CATALOG: dict[str, Any] = {
    "language": "python",
    "package_managers": {
        "uv.lock": "uv",
        "poetry.lock": "poetry",
        "Pipfile.lock": "pipenv",
        "Pipfile": "pipenv",
        "requirements.txt": "pip",
    },
    "frameworks": {
        # Web Frameworks
        "fastapi": {"name": "FastAPI", "type": "web_api"},
        "django": {"name": "Django", "type": "web_app"},
        "flask": {"name": "Flask", "type": "web_api"},
        "tornado": {"name": "Tornado", "type": "web_api"},
        "sanic": {"name": "Sanic", "type": "web_api"},
        "litestar": {"name": "Litestar", "type": "web_api"},
        "starlette": {"name": "Starlette", "type": "web_api"},
        # Database & ORM
        "sqlalchemy": {"name": "SQLAlchemy", "type": None},
        "tortoise-orm": {"name": "Tortoise-ORM", "type": None},
        "peewee": {"name": "Peewee", "type": None},
        "alembic": {"name": "Alembic", "type": None},
        "asyncpg": {"name": "asyncpg", "type": None},
        "psycopg2": {"name": "psycopg2", "type": None},
        "psycopg": {"name": "psycopg", "type": None},
        # Async & Workers
        "celery": {"name": "Celery", "type": None},
        "rq": {"name": "RQ", "type": None},
        # Scrapers & CLI
        "scrapy": {"name": "Scrapy", "type": "web_scraper"},
        "beautifulsoup4": {"name": "BeautifulSoup4", "type": "web_scraper"},
        "bs4": {"name": "BeautifulSoup4", "type": "web_scraper"},
        "click": {"name": "Click", "type": "cli"},
        "typer": {"name": "Typer", "type": "cli"},
        # Testing
        "pytest": {"name": "Pytest", "type": None},
        # Core & Data
        "pydantic": {"name": "Pydantic", "type": None},
        "httpx": {"name": "HTTPX", "type": None},
        "requests": {"name": "Requests", "type": None},
        "pandas": {"name": "Pandas", "type": None},
        "numpy": {"name": "NumPy", "type": None},
    },
    "entrypoint_files": [
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "wsgi.py",
        "asgi.py",
        "run.py",
        "cli.py",
    ],
    "scripts_dirs": [
        "scripts",
    ],
}
