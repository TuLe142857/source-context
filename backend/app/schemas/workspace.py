from pydantic import BaseModel, ConfigDict, EmailStr


class WorkspaceBase(BaseModel):
    workspace_name: str
    description: str | None = None


class WorkspaceCreate(WorkspaceBase):
    pass


class CreateWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    workspace_name: str | None = None
    description: str | None = None


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int


class AddMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    user_id: int | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int | None = None
    project_id: int | None = None
    user_id: int
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
