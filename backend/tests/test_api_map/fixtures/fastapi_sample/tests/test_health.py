from fastapi.testclient import TestClient

from shop.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").status_code == 200
