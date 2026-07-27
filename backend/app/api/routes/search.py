"""API route handlers for Code Search & Retrieval."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.model.branch import Branch
from app.model.repository import Repository
from app.model.workspace import Workspace
from app.retrieval.retriever import CodeRetriever
from app.schemas.search import (
    CodeSearchRequest,
    CodeSearchResponse,
    CodeSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Code Search & Retrieval"])


@router.post(
    "/code",
    response_model=CodeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve semantic code chunks by natural language prompt",
    description="Validates workspace_id and branch_id, embeds search query with Voyage AI, and returns top-k code hits from Qdrant.",
)
async def retrieve_code_post(
    request_data: CodeSearchRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> CodeSearchResponse:
    """Retrieves relevant code chunks for a given workspace and branch via POST payload.

    Args:
        request_data (CodeSearchRequest): Workspace ID, Branch ID, query string, and top_k limit.
        db (AsyncSession): Database session.
        current_user (User): Authenticated user.

    Returns:
        CodeSearchResponse: Ordered list of code search hits with similarity scores.
    """
    # 1. Validate workspace existence
    ws_res = await db.execute(
        select(Workspace).where(Workspace.id == request_data.workspace_id)
    )
    workspace = ws_res.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with ID {request_data.workspace_id} not found.",
        )

    # 2. Validate branch belongs to the specified workspace
    branch_res = await db.execute(
        select(Branch, Repository)
        .join(Repository, Branch.repository_id == Repository.id)
        .where(
            Branch.id == request_data.branch_id,
            Repository.project_id == request_data.workspace_id,
        )
    )
    if branch_res.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Branch with ID {request_data.branch_id} not found "
                f"or does not belong to workspace {request_data.workspace_id}."
            ),
        )

    # 3. Perform code retrieval via CodeRetriever
    retriever = CodeRetriever()
    hits = retriever.retrieve(query=request_data.query, top_k=request_data.top_k)

    results = [
        CodeSearchResult(
            score=hit.score,
            name=hit.name,
            kind=hit.kind,
            file_path=hit.file_path,
            signature=hit.signature,
            summary=hit.summary,
            docstring=hit.docstring,
            identifiers=hit.identifiers,
        )
        for hit in hits
    ]

    return CodeSearchResponse(
        workspace_id=request_data.workspace_id,
        branch_id=request_data.branch_id,
        query=request_data.query,
        total_hits=len(results),
        results=results,
    )


@router.get(
    "/code",
    response_model=CodeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve semantic code chunks via GET query parameters",
    description="Validates workspace_id and branch_id, embeds search query with Voyage AI, and returns top-k code hits from Qdrant.",
)
async def retrieve_code_get(
    workspace_id: Annotated[int, Query(..., description="Target Workspace ID")],
    branch_id: Annotated[int, Query(..., description="Target Branch ID")],
    query: Annotated[str, Query(..., min_length=1, description="Search query prompt")],
    db: DBSession,
    current_user: CurrentUser,
    top_k: Annotated[int, Query(ge=1, le=50, description="Top-k hits limit")] = 5,
) -> CodeSearchResponse:
    """Retrieves relevant code chunks for a given workspace and branch via GET query parameters."""
    request_data = CodeSearchRequest(
        workspace_id=workspace_id,
        branch_id=branch_id,
        query=query,
        top_k=top_k,
    )
    return await retrieve_code_post(
        request_data=request_data,
        db=db,
        current_user=current_user,
    )
