from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, overload

import httpx
from pydantic import TypeAdapter, ValidationError


@dataclass
class ApiResponse[T]:
    success: bool
    status_code: int
    data: T | None
    error_code: str | None
    message: str | None

    @staticmethod
    def ok(data: T | None, message: str | None = None, status_code: int = 200) -> ApiResponse[T]:
        return ApiResponse(
            success=True,
            status_code=status_code,
            data=data,
            message=message,
            error_code=None,
        )

    @staticmethod
    def error(status_code: int, error_code: str, message: str | None = None) -> ApiResponse:
        return ApiResponse(
            success=False,
            data=None,
            status_code=status_code,
            error_code=error_code,
            message=message,
        )


class ApiClient:
    def __init__(self, base_url: str, token: str, max_retry: int = 1):
        """
        Args:
            base_url: server url
            token: personal access token
        """
        self.server_url = base_url
        self.token = token
        self.max_retry = max_retry
        self.async_client = httpx.AsyncClient(
            base_url=self.server_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
            if len(token) > 0
            else None,
        )

    async def close(self):
        if self.async_client is not None:
            await self.async_client.aclose()

    def _parse_data(self, data: Any, response_model: type) -> Any:
        """
        Raises:
            ValidationError
        """
        adapter = TypeAdapter(response_model)
        return adapter.validate_python(data)

    async def _request(
        self,
        method: Literal["GET", "PUT", "POST", "PATCH", "DELETE"],
        path: str,
        response_model: type | None = None,
        **kwargs,
    ) -> ApiResponse[Any]:
        for attempt in range(self.max_retry):
            try:
                resp = await self.async_client.request(method, path, **kwargs)
                resp.raise_for_status()

                try:
                    raw_data = resp.json()
                except ValueError:
                    raw_data = resp.text

                if response_model is not None:
                    try:
                        parsed_data = self._parse_data(raw_data, response_model)
                        return ApiResponse.ok(data=parsed_data)
                    except ValidationError as e:
                        return ApiResponse.error(0, str(e))
                else:
                    return ApiResponse.ok(data=raw_data)

            except httpx.TimeoutException:
                if attempt < self.max_retry - 1:
                    continue
                return ApiResponse.error(
                    status_code=0,
                    error_code="REQUEST_TIMEOUT",
                )

            except httpx.ConnectError:
                if attempt < self.max_retry - 1:
                    continue
                return ApiResponse.error(
                    status_code=0,
                    error_code="CONNECTION_ERROR",
                )

            except httpx.HTTPError as exc:
                return ApiResponse.error(0, str(exc))

        return ApiResponse.error(0, "UNKNOW_ERROR", f"Request failed after {self.max_retry} attempts")

    @overload
    async def get(self, path: str, params: dict | None = None) -> ApiResponse[Any]: ...
    @overload
    async def get[M](self, path: str, params: dict | None = None, *, response_model: type[M]) -> ApiResponse[M]: ...
    async def get[M](self, path: str, params: dict | None = None, *, response_model: type[M] | None = None):
        return await self._request("GET", path, response_model=response_model, params=params)

    @overload
    async def post(self, path: str, json: dict | None = None) -> ApiResponse[Any]: ...
    @overload
    async def post[M](self, path: str, json: dict | None = None, *, response_model: type[M]) -> ApiResponse[M]: ...
    async def post[M](self, path: str, json: dict | None = None, *, response_model: type[M] | None = None):
        return await self._request("POST", path, response_model=response_model, json=json)

    @overload
    async def put(self, path: str, json: dict | None = None) -> ApiResponse[Any]: ...
    @overload
    async def put[M](self, path: str, json: dict | None = None, *, response_model: type[M]) -> ApiResponse[M]: ...
    async def put[M](self, path: str, json: dict | None = None, *, response_model: type[M] | None = None):
        return await self._request("PUT", path, response_model=response_model, json=json)

    @overload
    async def patch(self, path: str, json: dict | None = None) -> ApiResponse[Any]: ...
    @overload
    async def patch[M](self, path: str, json: dict | None = None, *, response_model: type[M]) -> ApiResponse[M]: ...
    async def patch[M](self, path: str, json: dict | None = None, *, response_model: type[M] | None = None):
        return await self._request("PATCH", path, response_model=response_model, json=json)

    @overload
    async def delete(self, path: str) -> ApiResponse[Any]: ...
    @overload
    async def delete[M](self, path: str, *, response_model: type[M]) -> ApiResponse[M]: ...
    async def delete[M](self, path: str, *, response_model: type[M] | None = None):
        return await self._request("DELETE", path, response_model=response_model)
