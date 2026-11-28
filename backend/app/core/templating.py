from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    select_autoescape,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class TemplateRenderer:
    """Render Jinja templates from a fixed directory."""

    def __init__(self, template_dir: str | Path = TEMPLATE_DIR):
        self.template_dir = Path(template_dir).resolve()
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html"]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """Render a template and return it as a string.

        Args:
            template_name: path relative to the template dir, e.g. "email/registration_otp".
                The ".html" suffix is optional.
            context: values for the template placeholders.

        Raises:
            TemplateNotFound: the template does not exist.
            jinja2.UndefinedError: the template uses a variable missing from context.
        """
        if not template_name.endswith(".html"):
            template_name += ".html"
        return self.env.get_template(template_name).render(**(context or {}))


@lru_cache
def get_template_renderer() -> TemplateRenderer:
    return TemplateRenderer()


__all__ = ["TemplateRenderer", "TemplateNotFound", "get_template_renderer"]