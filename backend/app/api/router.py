"""Top-level API router."""

from app.api.routes import api_router
from app.api.mcp import mcp_router

__all__ = ["api_router", "mcp_router"]
