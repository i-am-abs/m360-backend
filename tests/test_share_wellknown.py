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


from unittest.mock import MagicMock

from app.api.deps import get_broadcast_feed_service, get_masjid_entity_service
from app.exceptions.base import ApiException


@pytest.fixture
def share_client() -> TestClient:
    app = FastAPI()
    app.include_router(share_router)

    feed = MagicMock()
    feed.get_message_raw.return_value = {
        "id": "m1", "message_type": "video", "text": "Eid salah at 6:45 AM",
        "video_url": "https://stream.mux.com/a.m3u8",
        "thumbnail_url": "https://image.mux.com/a/thumbnail.jpg",
        "created_at": "2026-09-07T10:00:00+00:00", "masjid_id": "mid1",
    }
    masjid = MagicMock()
    masjid.get_masjid.return_value = {"masjid": {
        "id": "mid1", "place_id": "ChIJ1", "name": "Masjid Al Noor",
        "city": "Moradabad", "state": "UP", "photo_url": "",
        "management": {"is_claimed": True},
    }}
    app.dependency_overrides[get_broadcast_feed_service] = lambda: feed
    app.dependency_overrides[get_masjid_entity_service] = lambda: masjid
    return TestClient(app)


def test_share_page_renders_meta(share_client: TestClient):
    resp = share_client.get("/s/m1")
    assert resp.status_code == 200
    html = resp.text
    assert '<meta property="og:title" content="Masjid Al Noor"' in html
    assert 'twitter:card' in html
    assert "image.mux.com/a/thumbnail.jpg" in html
    assert "Eid salah at 6:45 AM" in html
    assert "Masjid Al Noor" in html
    assert "stream.mux.com/a.m3u8" in html
    assert resp.headers["cache-control"] == "public, max-age=300"


def test_share_page_404_for_missing(share_client: TestClient):
    from app.api.deps import get_broadcast_feed_service as dep
    share_client.app.dependency_overrides[dep] = lambda: _raising_feed()
    resp = share_client.get("/s/nope")
    assert resp.status_code == 404
    assert "no longer available" in resp.text.lower()


def _raising_feed():
    m = MagicMock()
    m.get_message_raw.side_effect = ApiException("Broadcast not found", status_code=404)
    return m
