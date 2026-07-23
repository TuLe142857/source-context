"""HTTP Client for communicating with the FastAPI backend."""

from typing import Any

import httpx

from .config import get_project_id_for_dir, load_config


class FastAPIClientError(Exception):
    """Exception raised when an error occurs during API communication."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FastAPIClient:
    """Async HTTP client wrapper for making requests to FastAPI backend.

    Attributes:
        server_url: Base API server URL.
        api_key: Bearer token / Personal Access Token for authentication.
    """

    def __init__(
        self,
        server_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        config = load_config()
        self.server_url = (server_url or config.server_url).rstrip("/")
        self.api_key = api_key or config.api_key

    def _get_headers(self, project_id: int | None = None) -> dict[str, str]:
        """Constructs headers required for FastAPI requests.

        Args:
            project_id: Optional explicit project ID.

        Returns:
            dict[str, str]: Map of HTTP header names to values.

        Raises:
            FastAPIClientError: If API Key is missing.
        """
        if not self.api_key:
            raise FastAPIClientError(
                "API Key is not configured. Please use 'setup_mcp_config' or CLI command to set API key."
            )

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if project_id is not None:
            headers["X-Project-ID"] = str(project_id)

        return headers

    async def request(
        self,
        method: str,
        path: str,
        project_id: int | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Sends an HTTP request to FastAPI backend.

        Args:
            method: HTTP method (e.g. GET, POST, DELETE).
            path: Relative API endpoint path starting with '/'.
            project_id: Optional project ID context.
            params: Query string parameters.
            json_data: JSON request payload body.

        Returns:
            Any: Decoded JSON response payload.

        Raises:
            FastAPIClientError: On network failures or non-2xx status codes.
        """
        headers = self._get_headers(project_id=project_id)
        url = f"{self.server_url}{path}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
            except httpx.RequestError as exc:
                raise FastAPIClientError(f"Failed to connect to FastAPI backend: {exc}") from exc

            if response.status_code == 401:
                raise FastAPIClientError("Unauthorized: Invalid or expired API Key.", status_code=401)
            if response.status_code == 403:
                raise FastAPIClientError("Forbidden: Access denied to requested resource.", status_code=403)
            if response.status_code >= 400:
                detail = response.text
                try:
                    err_json = response.json()
                    detail = err_json.get("detail", detail)
                except Exception:
                    pass
                raise FastAPIClientError(
                    f"API Error ({response.status_code}): {detail}",
                    status_code=response.status_code,
                )

            if response.status_code == 24:  # No Content
                return None

            return response.json()

    async def list_projects(self) -> list[dict[str, Any]]:
        """Retrieves list of accessible projects for current user.

        Returns:
            list[dict[str, Any]]: List of project dictionaries.
        """
        res = await self.request("GET", "/projects/")
        return res if isinstance(res, list) else []

    async def get_project(self, project_id: int) -> dict[str, Any]:
        """Retrieves details of a specific project by ID.

        Args:
            project_id: Target project ID.

        Returns:
            dict[str, Any]: Project details dictionary.
        """
        res = await self.request("GET", f"/projects/{project_id}")
        return res if isinstance(res, dict) else {}

    async def get_project_for_directory(self, dir_path: str) -> tuple[int | None, dict[str, Any] | None]:
        """Retrieves project details mapped to specified workspace directory.

        Args:
            dir_path: Absolute directory path.

        Returns:
            tuple[int | None, dict[str, Any] | None]: (project_id, project_detail)
        """
        project_id = get_project_id_for_dir(dir_path)
        if project_id is None:
            return None, None

        try:
            project_data = await self.get_project(project_id)
            return project_id, project_data
        except FastAPIClientError:
            return project_id, None
