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
    }
    masjid_svc = MagicMock()
    masjid_svc.get_masjid.return_value = {
        "masjid": {
            "id": "mid1", "place_id": "ChIJ1", "name": "Masjid Al Noor",
            "city": "Moradabad", "state": "UP", "address": "Civil Lines",
            "photo_url": "https://cdn/x.jpg", "management": {"is_claimed": True},
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
