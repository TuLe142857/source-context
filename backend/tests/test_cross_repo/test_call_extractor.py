from app.cross_repo.call_extractor import UniversalClientCallExtractor


def test_extract_python_requests_and_httpx():
    code = b'''
import requests
import httpx

def fetch_catalog_item(item_id: str):
    res = requests.get(f"http://catalog-service:8000/api/v1/products/{item_id}")
    return res.json()

def process_billing(order_data: dict):
    endpoint = "/api/v1/billing/invoices"
    resp = requests.post(endpoint, json=order_data)
    return resp.status_code

async def get_user_status(uid: str):
    client = httpx.AsyncClient()
    r = await client.get(f"https://auth.internal/api/v1/users/{uid}/status")
    return r.json()
'''
    extractor = UniversalClientCallExtractor()
    calls = extractor.extract_calls("services/client.py", code, project_id=1)

    assert len(calls) == 3
    # Check first call: GET /api/v1/products/{}
    assert calls[0].method == "GET"
    assert calls[0].canonical_path == "/api/v1/products/{}"
    assert calls[0].client_library == "requests/httpx"

    # Check second call: POST /api/v1/billing/invoices
    assert calls[1].method == "POST"
    assert calls[1].canonical_path == "/api/v1/billing/invoices"

    # Check third call: GET /api/v1/users/{}/status
    assert calls[2].method == "GET"
    assert calls[2].canonical_path == "/api/v1/users/{}/status"


def test_extract_typescript_axios_and_fetch():
    code = b'''
import axios from "axios";

export async function fetchOrderDetails(orderId: string) {
    const url = `/api/v1/orders/${orderId}`;
    const resp = await axios.get<OrderResponse>(url);
    return resp.data;
}

export async function loginUser(credentials: any) {
    const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials)
    });
    return response.json();
}
'''
    extractor = UniversalClientCallExtractor()
    calls = extractor.extract_calls("src/api/client.ts", code, project_id=2)

    assert len(calls) == 2
    # Check axios call
    assert calls[0].method == "GET"
    assert calls[0].canonical_path == "/api/v1/orders/{}"
    assert calls[0].client_library == "axios"

    # Check fetch call
    assert calls[1].method == "POST"
    assert calls[1].canonical_path == "/api/v1/auth/login"
    assert calls[1].client_library == "fetch"
