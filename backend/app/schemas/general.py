from pydantic import BaseModel


class RepositoryRequest(BaseModel):
    workspace_id: int


class BranchRequest(BaseModel):
    workspace_id: int
    repository_id: int
