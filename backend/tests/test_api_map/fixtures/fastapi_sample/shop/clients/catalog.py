import os
import requests
import httpx
from requests import Session

CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog:8000")
BASE = "http://billing:9000/api"


def get_product(pid: int):
    return requests.get(f"{CATALOG_URL}/api/v1/products/{pid}", timeout=5).json()


def charge(amount):
    url = BASE + "/charge"
    return requests.post(url, json={"amount": amount})


def patch_any(path):
    return requests.request("PATCH", f"{BASE}/{path}")


class UserClient:
    def __init__(self):
        self.client = httpx.Client(base_url="http://users:8000/api/v1")

    def fetch(self, user_id):
        return self.client.get(f"/users/{user_id}")


async def async_call():
    async with httpx.AsyncClient(base_url=CATALOG_URL) as client:
        r = await client.get("/api/v1/items/")
    return r


def with_session():
    s = Session()
    s.headers.update({"a": "b"})
    d = {}
    d.get("key")
    return s.delete("http://users:8000/api/v1/users/1")
