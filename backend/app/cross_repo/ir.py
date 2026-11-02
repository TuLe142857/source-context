from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ClientCallSite:
    """Represents an outgoing HTTP/RPC client call from source code."""

    caller_func_uid: Optional[str]
    """UID of the enclosing FunctionNode in Neo4j (if found)."""

    caller_func_name: str
    """Name of the function making the call, or 'anonymous'."""

    file_path: str
    """Relative path of the source file."""

    project_id: int
    """ID of the project containing the caller."""

    method: str
    """HTTP Method: GET, POST, PUT, DELETE, PATCH, ANY."""

    raw_path: str
    """Raw target URL argument from code (e.g. 'http://catalog:8000/api/v1/products/${id}')."""

    canonical_path: str
    """Normalized path template (e.g. '/api/v1/products/{}')."""

    client_library: str
    """Client library used: requests, httpx, axios, fetch, aiohttp..."""

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossRepoMatchResult:
    """Represents a discovered cross-repo link between a caller and a route."""

    caller_project_id: int
    caller_func_uid: Optional[str]
    caller_func_name: str
    caller_file: str
    call_path: str
    method: str

    target_project_id: int
    target_route_uid: str
    target_route_path: str
    target_handler_name: Optional[str]

    rule_level: str
    """Match level: 'exact_match', 'param_pattern', 'router_prefix'."""


@dataclass
class WorkspaceCrossRepoSummary:
    """Summary of cross-repo matching pass for a workspace."""

    workspace_id: int
    links_created: int = 0
    calls_scanned: int = 0
    routes_scanned: int = 0
    local_calls_filtered: int = 0
    details: list[CrossRepoMatchResult] = field(default_factory=list)
