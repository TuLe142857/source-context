from app.route_extractor.normalizer import canonicalize_url_path


def test_canonicalize_url_path_basic():
    assert canonicalize_url_path("/api/v1/products") == "/api/v1/products"
    assert canonicalize_url_path("/api/v1/products/") == "/api/v1/products"
    assert canonicalize_url_path("api/v1/products") == "/api/v1/products"
    assert canonicalize_url_path("") == "/"


def test_canonicalize_url_path_strips_host_and_query():
    assert (
        canonicalize_url_path("http://localhost:8000/api/v1/products?limit=10#section")
        == "/api/v1/products"
    )
    assert (
        canonicalize_url_path("https://api.my-domain.com/v2/orders")
        == "/v2/orders"
    )


def test_canonicalize_url_path_fastapi_and_express_params():
    # FastAPI {user_id}
    assert canonicalize_url_path("/api/v1/users/{user_id}") == "/api/v1/users/{}"
    # Express :userId
    assert canonicalize_url_path("/api/v1/users/:userId") == "/api/v1/users/{}"
    # Flask <invoice_id> / <int:id>
    assert canonicalize_url_path("/api/v1/billing/<int:id>") == "/api/v1/billing/{}"
    assert canonicalize_url_path("/api/v1/invoices/<invoice_id>") == "/api/v1/invoices/{}"
    # Next.js [id]
    assert canonicalize_url_path("/api/products/[id]") == "/api/products/{}"
