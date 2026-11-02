import asyncio
from unittest.mock import AsyncMock, patch
from app.cross_repo.service import CrossRepoService


def test_caller_local_floor_prevents_false_positive():
    """Verify that if a caller's own repository has a matching route, it is treated as local
    and NOT linked cross-repo even if another repository has the same route.
    """
    service = CrossRepoService()
    service._resolve_workspace_projects = AsyncMock(
        return_value={
            1: {"project_id": 1, "project_name": "p1", "repo_id": 10, "repo_name": "repo_1"},
            2: {"project_id": 2, "project_name": "p2", "repo_id": 20, "repo_name": "repo_2"},
        }
    )

    mock_calls = [
        (
            "call_uid_1",
            "GET",
            "/api/v1/health",
            "/api/v1/health",
            "src/caller.py",
            "check_health",
            1,  # project_id
            "fn_uid_1",
            "check_health",
        )
    ]

    mock_routes = [
        # Route in Repo 1 (Local Route)
        (
            "route_uid_local",
            "GET",
            "/api/v1/health",
            "/api/v1/health",
            1,  # project_id
            "fn_uid_local",
            "health_handler",
            "FastAPI",
        ),
        # Route in Repo 2 (Remote Route)
        (
            "route_uid_remote",
            "GET",
            "/api/v1/health",
            "/api/v1/health",
            2,  # project_id
            "fn_uid_remote",
            "remote_health_handler",
            "FastAPI",
        ),
    ]

    with patch("neomodel.db.cypher_query") as mock_cypher:
        mock_cypher.side_effect = [
            (mock_calls, None),
            (mock_routes, None),
        ]

        summary = asyncio.run(service.match_and_link_workspace(workspace_id=99))

        assert summary.calls_scanned == 1
        assert summary.routes_scanned == 2
        assert summary.local_calls_filtered == 1
        assert summary.links_created == 0


def test_cross_repo_link_established():
    """Verify that when caller repo does NOT have a local route, but a target repo does,
    a cross-repo link is created.
    """
    service = CrossRepoService()
    service._resolve_workspace_projects = AsyncMock(
        return_value={
            1: {"project_id": 1, "project_name": "order_service", "repo_id": 10, "repo_name": "repo_1"},
            2: {"project_id": 2, "project_name": "catalog_service", "repo_id": 20, "repo_name": "repo_2"},
        }
    )

    mock_calls = [
        (
            "call_uid_order",
            "GET",
            "http://catalog:8000/api/v1/products/prod_100",
            "/api/v1/products/{}",
            "order_service/client.py",
            "get_product",
            1,  # project_id
            "fn_uid_get_product",
            "get_product",
        )
    ]

    mock_routes = [
        (
            "route_uid_catalog_product",
            "GET",
            "/api/v1/products/{}",
            "/api/v1/products/{product_id}",
            2,  # project_id
            "fn_uid_catalog_handler",
            "get_product_by_id",
            "FastAPI",
        ),
    ]

    with patch("neomodel.db.cypher_query") as mock_cypher:
        mock_cypher.side_effect = [
            (mock_calls, None),
            (mock_routes, None),
            (None, None),  # link call cypher
            (None, None),  # link func cypher
        ]

        summary = asyncio.run(service.match_and_link_workspace(workspace_id=99))

        assert summary.calls_scanned == 1
        assert summary.routes_scanned == 1
        assert summary.local_calls_filtered == 0
        assert summary.links_created == 1
        assert len(summary.details) == 1

        detail = summary.details[0]
        assert detail.caller_project_id == 1
        assert detail.target_project_id == 2
        assert detail.target_route_path == "/api/v1/products/{}"
        assert detail.rule_level == "param_pattern"
