from pydantic import BaseModel, Field


class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search prompt")
    top_k: int = Field(default=5, ge=1, le=50, description="Max search results")
