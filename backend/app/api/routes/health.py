"""Health-check API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check backend health",
)
def read_health(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> HealthResponse:
    """Return the current backend service status."""

    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
