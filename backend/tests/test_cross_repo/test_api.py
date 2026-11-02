from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.cross_repo.ir import WorkspaceCrossRepoSummary, CrossRepoMatchResult


def test_cross_repo_link_sync_endpoint(client: TestClient):
    mock_summary = WorkspaceCrossRepoSummary(
        workspace_id=42,
        links_created=1,
        calls_scanned=2,
        routes_scanned=5,
        local_calls_filtered=1,
        details=[
            CrossRepoMatchResult(
                caller_project_id=1,
                caller_func_uid="fn_1",
                caller_func_name="create_order",
                caller_file="services/order.py",
                call_path="http://catalog:8000/api/v1/products/123",
                method="GET",
                target_project_id=2,
                target_route_uid="route_2",
                target_route_path="/api/v1/products/{}",
                target_handler_name="get_product",
                rule_level="param_pattern",
            )
        ],
    )

    with patch("app.api.routes.cross_repo.get_cross_repo_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.match_and_link_workspace = AsyncMock(return_value=mock_summary)
        mock_get_svc.return_value = mock_svc

        response = client.post("/api/v1/cross-repo/42/link?sync=true")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["workspace_id"] == 42
        assert data["links_created"] == 1
        assert data["calls_scanned"] == 2
        assert data["local_calls_filtered"] == 1
        assert len(data["details"]) == 1
        assert data["details"][0]["call_path"] == "http://catalog:8000/api/v1/products/123"


def test_cross_repo_get_links_endpoint(client: TestClient):
    mock_links = [
        {
            "caller_repo": "repo_1",
            "caller_project": "order_service",
            "caller_file": "client.py",
            "caller_func_name": "fetch_product",
            "method": "GET",
            "call_path": "/api/v1/products/1",
            "target_repo": "repo_2",
            "target_project": "catalog_service",
            "target_route_path": "/api/v1/products/{}",
            "target_handler_name": "get_product_by_id",
            "rule_level": "param_pattern",
        }
    ]

    with patch("app.api.routes.cross_repo.get_cross_repo_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_cross_repo_links_for_workspace = AsyncMock(return_value=mock_links)
        mock_get_svc.return_value = mock_svc

        response = client.get("/api/v1/cross-repo/42/links")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["caller_repo"] == "repo_1"
        assert data[0]["target_repo"] == "repo_2"


def test_cross_repo_clear_links_endpoint(client: TestClient):
    with patch("app.api.routes.cross_repo.get_cross_repo_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.clear_cross_repo_links = AsyncMock(return_value=1)
        mock_get_svc.return_value = mock_svc

        response = client.delete("/api/v1/cross-repo/42/links")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "cleared"
        mock_svc.clear_cross_repo_links.assert_awaited_once_with(42)
