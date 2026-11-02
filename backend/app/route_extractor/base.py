from abc import ABC, abstractmethod
from typing import Sequence
from app.parser.uast import UASTNode
from .models import ExtractedRoute


class BaseRouteExtractor(ABC):
    """Abstract base class for framework-specific route extractors."""

    language: str
    """Language target: 'python', 'typescript', 'javascript'."""

    framework_name: str
    """Framework name (e.g. 'fastapi', 'flask', 'django', 'express', 'nestjs', 'nextjs', 'fastify')."""

    @abstractmethod
    def extract_routes(
        self,
        file_path: str,
        code_bytes: bytes,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ExtractedRoute]:
        """Extract all endpoint routes defined in this file.

        Args:
            file_path: Relative path of the file from project root.
            code_bytes: Raw source code bytes.
            uast_root: Optional pre-parsed UAST node for this file.

        Returns:
            Sequence of ExtractedRoute objects.
        """
        pass
