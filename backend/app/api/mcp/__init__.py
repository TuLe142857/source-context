from fastapi import APIRouter
from .graph import router as graph_router




mcp_router = APIRouter(prefix="/mcp/v1", tags=["MCP"])

mcp_router.include_router(graph_router)

