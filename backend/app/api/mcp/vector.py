"""Vector search API router endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentAgent, VectorServiceDep
from app.retrieval.retriever import QueryResult

router = APIRouter(prefix="/vector", tags=["Vector"])


class SearchRequest(BaseModel):
    """Payload schema for code vector search requests."""

    query: str = Field(..., min_length=1, description="Natural language search prompt")
    top_k: int = Field(default=5, ge=1, le=50, description="Max search results")


@router.post("/search/{repository_id}/{branch_name}")
async def search_cross_repository(
    request: SearchRequest,
    current_agent: CurrentAgent,
    vector_service: VectorServiceDep,
    repository_id: int,
    branch_name: str,
) -> list[QueryResult]:
    """Search code chunks within a specific repository branch (PAT Authenticated)."""
    return await vector_service.search_with_branch_filter(
        repository_id=repository_id,
        branch_name=branch_name,
        query=request.query,
        top_k=request.top_k,
    )


@router.post("/search/{workspace_id}")
async def search_workspace(
    request: SearchRequest,
    current_agent: CurrentAgent,
    vector_service: VectorServiceDep,
    workspace_id: int,
) -> list[QueryResult]:
    """Search code chunks across a workspace (PAT Authenticated)."""
    return await vector_service.search(
        workspace_id=workspace_id,
        query=request.query,
        top_k=request.top_k,
    )
