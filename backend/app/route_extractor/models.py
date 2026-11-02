from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ExtractedRoute:
    """An HTTP/RPC endpoint extracted from code."""

    method: str
    """HTTP method (GET, POST, PUT, DELETE, PATCH, etc.) or RPC action."""

    path: str
    """Canonical path template with '{}' placeholders (e.g. '/api/v1/users/{}')."""

    raw_path: str
    """Original path defined in the code (e.g. '/api/v1/users/:id' or '/api/v1/users/{user_id}')."""

    framework: str
    """Framework name (fastapi, flask, django, express, nestjs, fastify, nextjs, etc.)."""

    protocol: str = "http"
    """Protocol type: http, grpc, websocket."""

    handler_name: Optional[str] = None
    """Name of the handler function or method if identified."""

    handler_start_byte: Optional[int] = None
    """Start byte of the handler definition in file content."""

    handler_end_byte: Optional[int] = None
    """End byte of the handler definition in file content."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (e.g. decorators, tags, query parameters)."""
