import httpx


class ApiClient:
    def __init__(self, base_url: str, token: str):
        """
        Args:
            base_url: server url
            token: personal access token
        """
        self.server_url = base_url
        self.token = token
        self.async_client = httpx.AsyncClient(
            base_url=self.server_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )

    pass
