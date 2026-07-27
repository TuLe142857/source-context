"""Schemas for Code Search & Retrieval API endpoints."""

from pydantic import BaseModel, Field


class CodeSearchRequest(BaseModel):
    """Payload schema for code retrieval request."""

    workspace_id: int = Field(..., description="Target Workspace ID", examples=[1])
    branch_id: int = Field(..., description="Target Branch ID", examples=[1])
    query: str = Field(
        ...,
        min_length=1,
        description="Natural language search prompt or query",
        examples=["hàm phân trang danh sách items cho superuser"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top search results to return",
        examples=[5],
    )


class CodeSearchResult(BaseModel):
    """Schema representing a single code hit from retrieval engine."""

    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    name: str = Field(..., description="Name of the function or class construct")
    kind: str = Field(..., description="Construct type (function, class, etc.)")
    file_path: str = Field(..., description="Relative or full file path")
    signature: str = Field(..., description="Function or class signature")
    summary: str | None = Field(default=None, description="AI semantic summary")
    docstring: str | None = Field(
        default=None, description="Original docstring if available"
    )
    identifiers: list[str] = Field(
        default_factory=list, description="Extracted code identifiers"
    )


class CodeSearchResponse(BaseModel):
    """Response schema for code retrieval query."""

    workspace_id: int
    branch_id: int
    query: str
    total_hits: int
    results: list[CodeSearchResult]
