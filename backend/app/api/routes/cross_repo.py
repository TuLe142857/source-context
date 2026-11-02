import logging
from typing import Any
from fastapi import APIRouter, Query

from app.core import APIResponse
from app.cross_repo.service import get_cross_repo_service
from app.tasks.cross_repo import link_workspace_cross_repo_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cross-repo", tags=["Cross-Repo Intelligence"])


@router.post(
    "/{workspace_id}/link",
    summary="Trigger cross-repo HTTP matching for a workspace",
)
async def trigger_cross_repo_linking(
    workspace_id: int,
    sync: bool = Query(default=False, description="Run synchronously and return results immediately"),
) -> APIResponse:
    logger.info("[API /cross-repo/%d/link] Received cross-repo matching request (sync=%s)", workspace_id, sync)

    if sync:
        service = get_cross_repo_service()
        summary = await service.match_and_link_workspace(workspace_id)
        return APIResponse.ok(
            data={
                "workspace_id": summary.workspace_id,
                "links_created": summary.links_created,
                "calls_scanned": summary.calls_scanned,
                "routes_scanned": summary.routes_scanned,
                "local_calls_filtered": summary.local_calls_filtered,
                "details": [
                    {
                        "caller_project_id": d.caller_project_id,
                        "caller_func_uid": d.caller_func_uid,
                        "caller_func_name": d.caller_func_name,
                        "caller_file": d.caller_file,
                        "call_path": d.call_path,
                        "method": d.method,
                        "target_project_id": d.target_project_id,
                        "target_route_uid": d.target_route_uid,
                        "target_route_path": d.target_route_path,
                        "target_handler_name": d.target_handler_name,
                        "rule_level": d.rule_level,
                    }
                    for d in summary.details
                ],
            }
        )

    task = link_workspace_cross_repo_task.delay(workspace_id)
    logger.info("[API /cross-repo/%d/link] Enqueued background task %s to Celery worker", workspace_id, task.id)
    return APIResponse.ok(data={"task_id": str(task.id), "status": "queued"})


@router.get(
    "/{workspace_id}/links",
    summary="Get all cross-repo links in a workspace",
)
async def get_cross_repo_links(workspace_id: int) -> APIResponse:
    logger.info("[API /cross-repo/%d/links] Fetching all cross-repo links for workspace %d", workspace_id, workspace_id)
    service = get_cross_repo_service()
    links = await service.get_cross_repo_links_for_workspace(workspace_id)
    logger.info("[API /cross-repo/%d/links] Found %d active cross-repo link(s)", workspace_id, len(links))
    return APIResponse.ok(data=links)


@router.delete(
    "/{workspace_id}/links",
    summary="Clear all cross-repo links in a workspace",
)
async def clear_cross_repo_links(workspace_id: int) -> APIResponse:
    logger.info("[API /cross-repo/%d/links] Clearing all cross-repo links for workspace %d", workspace_id, workspace_id)
    service = get_cross_repo_service()
    await service.clear_cross_repo_links(workspace_id)
    return APIResponse.ok(data={"status": "cleared"})
