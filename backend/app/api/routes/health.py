"""Health check API endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Check backend service health")
@router.get("/", summary="Check backend service health")
async def health_check() -> dict[str, str]:
    """Returns status of backend service."""
    return {"status": "ok"}
