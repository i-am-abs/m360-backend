from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MONGODB_ENABLED", "false")

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_broadcast_feed_service, get_masjid_entity_service
from app.api.v1.endpoints.broadcast import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    feed_svc = MagicMock()
    feed_svc.get_message_raw.return_value = {
        "id": "m1", "message_type": "video", "text": "hello",
        "video_url": "https://stream.mux.com/a.m3u8",
        "thumbnail_url": "https://image.mux.com/a/thumbnail.jpg",
        "created_at": "2026-09-07T10:00:00+00:00", "masjid_id": "mid1",
        # sensitive fields that must NOT leak to unauthenticated callers
        "reactions": {"like": ["u1", "u2"]},
        "comments": [{"user_id": "u9", "text": "secret"}],
        "sender": {"user_id": "u_admin", "name": "Admin"},
        "mux_asset_id": "asset_123", "mux_upload_id": "upload_123",
        "view_count": 42,
    }
    masjid_svc = MagicMock()
    masjid_svc.get_masjid.return_value = {
        "masjid": {
            "id": "mid1", "place_id": "ChIJ1", "name": "Masjid Al Noor",
            "city": "Moradabad", "state": "UP", "address": "Civil Lines",
            "photo_url": "https://cdn/x.jpg", "management": {"is_claimed": True},
            "location": {"type": "Point", "coordinates": [78.7733, 28.8386]},
        }
    }
    app.dependency_overrides[get_broadcast_feed_service] = lambda: feed_svc
    app.dependency_overrides[get_masjid_entity_service] = lambda: masjid_svc
    return TestClient(app)


def test_public_broadcast_includes_masjid_extras(client: TestClient):
    resp = client.get("/api/v1/broadcast/public/m1")
    assert resp.status_code == 200
    masjid = resp.json()["data"]["masjid"]
    assert masjid["id"] == "mid1"
    assert masjid["place_id"] == "ChIJ1"
    assert masjid["state"] == "UP"
    assert masjid["verified"] is True
    assert masjid["photo_url"] == "https://cdn/x.jpg"
    assert masjid["name"] == "Masjid Al Noor"


def test_public_broadcast_includes_coordinates(client: TestClient):
    resp = client.get("/api/v1/broadcast/public/m1")
    assert resp.status_code == 200
    masjid = resp.json()["data"]["masjid"]
    assert masjid["latitude"] == pytest.approx(28.8386)
    assert masjid["longitude"] == pytest.approx(78.7733)


def test_public_broadcast_lat_lng_dict_shape():
    from app.api.v1.endpoints.broadcast import _masjid_lat_lng

    assert _masjid_lat_lng({"location": {"lat": 12.5, "lng": 77.1}}) == (12.5, 77.1)
    assert _masjid_lat_lng({"location": {"type": "Point", "coordinates": [77.1, 12.5]}}) == (12.5, 77.1)
    assert _masjid_lat_lng({}) == (0.0, 0.0)
    assert _masjid_lat_lng({"location": {"lat": None, "lng": None}}) == (0.0, 0.0)


def test_public_broadcast_does_not_leak_sensitive_message_fields(client: TestClient):
    resp = client.get("/api/v1/broadcast/public/m1")
    assert resp.status_code == 200
    message = resp.json()["data"]["message"]
    for leaked in ("reactions", "comments", "sender", "mux_asset_id", "mux_upload_id", "view_count"):
        assert leaked not in message
    assert set(message) <= {
        "id", "masjid_id", "message_type", "text", "video_url", "thumbnail_url", "created_at",
    }
    assert message["id"] == "m1"
    assert message["text"] == "hello"
