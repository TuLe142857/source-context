from app.route_extractor.service import get_route_indexing_service


def test_express_routes_and_subrouter_prefix():
    service = get_route_indexing_service()
    code = b"""
import express, { Router } from "express";
const app = express();
const webhookRouter = Router();

webhookRouter.post("/payment-callback", (req, res) => {
    res.json({ ok: true });
});

app.use("/api/v1/webhooks", webhookRouter);
"""
    routes = service.extract_routes_from_file("src/webhooks/server.ts", code)
    assert len(routes) == 1
    r = routes[0]
    assert r.method == "POST"
    assert r.raw_path == "/api/v1/webhooks/payment-callback"
    assert r.path == "/api/v1/webhooks/payment-callback"
    assert r.framework == "express"


def test_nestjs_controller_and_method_decorators():
    service = get_route_indexing_service()
    code = b"""
import { Controller, Get, Post, Param } from '@nestjs/common';

@Controller('api/v1/users')
export class UsersController {
    @Get()
    findAll() {
        return [];
    }

    @Get(':id')
    findOne(@Param('id') id: string) {
        return { id };
    }

    @Post()
    create() {
        return {};
    }
}
"""
    routes = service.extract_routes_from_file("src/users.controller.ts", code)
    assert len(routes) == 3
    paths = {r.method: r.path for r in routes}
    assert paths["POST"] == "/api/v1/users"
    assert "/api/v1/users/{}" in paths.values()
    assert "/api/v1/users" in paths.values()


def test_nextjs_app_router_extraction():
    service = get_route_indexing_service()
    code = b"""
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
    return NextResponse.json({ items: [] });
}

export async function POST(request: Request) {
    return NextResponse.json({ created: true });
}
"""
    routes = service.extract_routes_from_file(
        "app/api/products/[productId]/route.ts", code
    )
    assert len(routes) == 2
    methods = {r.method for r in routes}
    assert methods == {"GET", "POST"}
    for r in routes:
        assert r.path == "/api/products/{}"
        assert r.framework == "nextjs_app_router"
