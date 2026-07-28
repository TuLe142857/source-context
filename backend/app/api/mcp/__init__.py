from fastapi import APIRouter
from .graph import router as graph_router
from .vector import router as vector_router


mcp_router = APIRouter(prefix="/mcp/v1", tags=["MCP"])

mcp_router.include_router(graph_router)
mcp_router.include_router(vector_router)
