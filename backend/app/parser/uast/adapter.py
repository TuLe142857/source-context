from dataclasses import dataclass, field

from tree_sitter import Query

from .handlers import CaptureHandler
from .node_builder import UASTNodeFactory
from .types import CaptureType


@dataclass(frozen=True, kw_only=True)
class LanguageAdapter:
    @staticmethod
    def get_default_capture_priorities() -> dict[CaptureType, int]:
        return {"definition.method": 2, "definition.constructor": 1}

    """

    Attributes:
        language_name:
        query:
        node_factory:
        handlers:

    """

    language_name: str
    query: Query
    node_factory: UASTNodeFactory = field(default_factory=UASTNodeFactory)
    handlers: list[CaptureHandler]
    capture_priorities: dict[CaptureType, int] = field(default_factory=get_default_capture_priorities)

    def get_capture_priorities(self, capture: CaptureType) -> int:
        return self.capture_priorities.get(capture, 100)
