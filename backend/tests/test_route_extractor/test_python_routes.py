from app.route_extractor.service import get_route_indexing_service


def test_fastapi_route_extraction_basic():
    service = get_route_indexing_service()
    code = b"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/products")
def list_products():
    return []

@app.post("/api/v1/products/{product_id}")
async def update_product(product_id: str):
    return {"id": product_id}
"""
    routes = service.extract_routes_from_file("app/main.py", code)
    assert len(routes) == 2
    r1, r2 = routes[0], routes[1]

    assert r1.method == "GET"
    assert r1.path == "/api/v1/products"
    assert r1.handler_name == "list_products"
    assert r1.framework == "fastapi"

    assert r2.method == "POST"
    assert r2.path == "/api/v1/products/{}"
    assert r2.handler_name == "update_product"


def test_fastapi_apirouter_prefix_resolution():
    service = get_route_indexing_service()
    code = b"""
from fastapi import APIRouter
inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

@inventory_router.post("/reserve")
def reserve_stock():
    return {"status": "ok"}
"""
    routes = service.extract_routes_from_file("routers/inventory.py", code)
    assert len(routes) == 1
    r = routes[0]
    assert r.method == "POST"
    assert r.raw_path == "/api/v1/inventory/reserve"
    assert r.path == "/api/v1/inventory/reserve"
    assert r.handler_name == "reserve_stock"


def test_flask_blueprint_url_prefix_resolution():
    service = get_route_indexing_service()
    code = b"""
from flask import Blueprint
billing_bp = Blueprint("billing", __name__, url_prefix="/api/v1/billing")

@billing_bp.route("/charge", methods=["POST"])
def charge_customer():
    return {}

@billing_bp.route("/invoices/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    return {}
"""
    routes = service.extract_routes_from_file("billing/app.py", code)
    assert len(routes) == 2
    assert routes[0].method == "POST"
    assert routes[0].path == "/api/v1/billing/charge"
    assert routes[0].handler_name == "charge_customer"

    assert routes[1].method == "GET"
    assert routes[1].path == "/api/v1/billing/invoices/{}"
    assert routes[1].handler_name == "get_invoice"


def test_django_urlpatterns_extraction():
    service = get_route_indexing_service()
    code = b"""
from django.urls import path, re_path
from . import views

urlpatterns = [
    path('api/v1/orders/', views.order_list),
    path('api/v1/orders/<int:order_id>/', views.order_detail),
]
"""
    routes = service.extract_routes_from_file("mysite/urls.py", code)
    assert len(routes) == 2
    assert routes[0].path == "/api/v1/orders"
    assert routes[0].handler_name == "order_list"

    assert routes[1].path == "/api/v1/orders/{}"
    assert routes[1].handler_name == "order_detail"
