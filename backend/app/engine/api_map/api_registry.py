from collections.abc import Sequence

from .handlers.api_handler import ApiHandler


class ApiRegistry:
    """Handlers by language (detection) and by kind (matching)."""

    def __init__(self, handlers: Sequence[ApiHandler] = ()) -> None:
        self._handlers: list[ApiHandler] = list(handlers)

    def register(self, handler: ApiHandler) -> None:
        self._handlers.append(handler)

    def handlers(self) -> list[ApiHandler]:
        return list(self._handlers)

    def handlers_for(self, language: str) -> list[ApiHandler]:
        return [handler for handler in self._handlers if language in handler.languages]

    def languages(self) -> set[str]:
        return {
            language for handler in self._handlers for language in handler.languages
        }

    def matcher(self, kind: str) -> ApiHandler | None:
        """Any handler of the protocol: matching is protocol-level, shared by every language."""

        return next(
            (handler for handler in self._handlers if handler.kind == kind), None
        )
