from fastapi import APIRouter

from app.api.mcp.vector import router as search_router
from app.api.routes.auth import router as auth_router
from app.api.routes.branches import router as branches_router
from app.api.routes.health import router as health_router
from app.api.routes.indexing import router as indexing_router
from app.api.routes.pats import router as pats_router
from app.api.routes.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(pats_router)
api_router.include_router(workspaces_router)
api_router.include_router(branches_router)
api_router.include_router(indexing_router)
api_router.include_router(search_router)
