import asyncio
import logging
from celery import shared_task  # type: ignore[import-untyped]
from app.cross_repo.service import get_cross_repo_service

logger = logging.getLogger(__name__)


@shared_task(name="link_workspace_cross_repo_task")
def link_workspace_cross_repo_task(workspace_id: int) -> dict:
    """Celery background task for running cross-repo matching across all projects in a workspace.

    Args:
        workspace_id (int): Target workspace ID.

    Returns:
        dict: Summary of matching results.
    """
    logger.info("Starting cross-repo linking task for workspace %d", workspace_id)
    try:
        service = get_cross_repo_service()
        summary = asyncio.run(service.match_and_link_workspace(workspace_id))
        logger.info(
            "Finished cross-repo linking task for workspace %d: %d links created",
            workspace_id,
            summary.links_created,
        )
        return {
            "workspace_id": summary.workspace_id,
            "calls_scanned": summary.calls_scanned,
            "routes_scanned": summary.routes_scanned,
            "local_calls_filtered": summary.local_calls_filtered,
            "links_created": summary.links_created,
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
    except Exception as exc:
        logger.exception("Error during cross-repo linking for workspace %d: %s", workspace_id, exc)
        raise exc
