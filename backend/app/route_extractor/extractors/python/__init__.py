# Auto-register all python route extractors
from . import fastapi
from . import flask
from . import django
from . import litestar_sanic

__all__ = ["fastapi", "flask", "django", "litestar_sanic"]
