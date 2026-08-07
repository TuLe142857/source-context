from fastapi import Depends

from typing import Annotated

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / ".." / "templates"


class TemplateService:
    def __init__(self, template_dir: str | Path = TEMPLATE_DIR):
        if isinstance(template_dir, str):
            self.template_dir = Path(template_dir).resolve()
        else:
            self.template_dir = template_dir.resolve()

        self.env: Environment = Environment(loader=FileSystemLoader(self.template_dir))

    def render(self, template_name: str, context: dict | None = None) -> str:
        """

        Args:
            template_name: template name, can have prefix .html or not
            context: content to fill template placeholder

        Returns:
            Rendered content as string
        """
        if not template_name.endswith(".html"):
            template_name = template_name + ".html"
        template = self.env.get_template(template_name)

        if context is None:
            return template.render()
        else:
            return template.render(**context)


def get_template_service() -> TemplateService:
    return TemplateService()


TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
