from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MONGODB_ENABLED", "false")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware
from app.services.rate_limiter import InMemoryRateLimitBackend, RateLimiter


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.get("/.well-known/assetlinks.json")
    def assetlinks():
        return []

    @app.get("/s/{message_id}")
    def share(message_id: str):
        return {"id": message_id}

    @app.get("/share-static/logo.png")
    def static_asset():
        return {"ok": True}

    @app.get("/api/v1/thing")
    def thing():
        return {"ok": True}

    limiter = RateLimiter(
        InMemoryRateLimitBackend(),
        default_limit=3,
        auth_limit=3,
        window_seconds=60,
    )
    app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)
    return TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/.well-known/assetlinks.json",
        "/s/abc123",
        "/share-static/logo.png",
    ],
)
def test_public_web_paths_are_never_rate_limited(client: TestClient, path: str):
    for _ in range(25):
        resp = client.get(path)
        assert resp.status_code != 429


def test_other_paths_still_rate_limited(client: TestClient):
    codes = [client.get("/api/v1/thing").status_code for _ in range(10)]
    assert 429 in codes
