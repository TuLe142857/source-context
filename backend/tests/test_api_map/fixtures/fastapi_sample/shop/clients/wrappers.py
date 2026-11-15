import requests


class ApiClient:
    def __init__(self, base: str):
        self.base = base

    def get(self, path: str):
        return requests.get(self.base + path)


api = ApiClient("http://orders:8000")


def list_orders():
    return api.get("/orders")


def cached_user(key):
    cache = {}
    return cache.get("/users/" + key)
