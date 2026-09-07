from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MONGODB_ENABLED", "false")
os.environ["APP_ENV"] = "test"
os.environ["ANDROID_SHA256_CERT_FINGERPRINTS"] = "AA:BB:CC,DD:EE:FF"
os.environ["APPLE_TEAM_ID"] = "ABCDE12345"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.web.share import router as share_router


@pytest.fixture(autouse=True)
def _reset_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(share_router)
    return TestClient(app)


def test_assetlinks_json(client: TestClient):
    resp = client.get("/.well-known/assetlinks.json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body[0]["relation"] == ["delegate_permission/common.handle_all_urls"]
    target = body[0]["target"]
    assert target["namespace"] == "android_app"
    assert target["package_name"] == "com.starkinnovations.m360"
    assert target["sha256_cert_fingerprints"] == ["AA:BB:CC", "DD:EE:FF"]


def test_apple_app_site_association(client: TestClient):
    resp = client.get("/.well-known/apple-app-site-association")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    details = body["applinks"]["details"][0]
    assert details["appID"] == "ABCDE12345.com.starkinnovations.m360"
    assert details["paths"] == ["/s/*"]
