from pydantic import BaseModel


class RepositoryRequest(BaseModel):
    workspace_id: int


class BranchRequest(BaseModel):
    workspace_id: int
    repository_id: int


class BranchProjectsRequest(BaseModel):
    workspace_id: int
    repo_id: int
    branch_name: str
