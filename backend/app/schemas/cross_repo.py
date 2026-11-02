from typing import Any, Optional
from pydantic import BaseModel, Field


class CrossRepoMatchDetail(BaseModel):
    caller_repo: Optional[str] = None
    caller_project: Optional[str] = None
    caller_file: Optional[str] = None
    caller_func_name: Optional[str] = None
    caller_func_uid: Optional[str] = None
    method: str
    call_path: str
    call_canonical_path: Optional[str] = None
    client_library: Optional[str] = None
    target_repo: Optional[str] = None
    target_project: Optional[str] = None
    target_route_path: str
    target_framework: Optional[str] = None
    target_handler_name: Optional[str] = None
    target_handler_uid: Optional[str] = None
    rule_level: str


class CrossRepoSummaryResponse(BaseModel):
    workspace_id: int
    links_created: int
    calls_scanned: int
    routes_scanned: int
    local_calls_filtered: int
    details: list[dict[str, Any]] = Field(default_factory=list)
