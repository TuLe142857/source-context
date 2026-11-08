from fastapi import FastAPI
from shop.routers import users
from shop.routers.items import router as items_router

app = FastAPI(root_path="/svc")
API_PREFIX = "/api/v1"

app.include_router(users.router, prefix=API_PREFIX)
app.include_router(items_router, prefix="/api/v1/items", tags=["items"])


@app.get("/health")
async def health():
    return {"ok": True}


@app.api_route("/echo", methods=["GET", "POST"])
def echo():
    return {}
