from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MONGODB_ENABLED", "false")

from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.web.share_context import build_share_context


@pytest.fixture
def settings() -> Settings:
    return Settings(
        share_web_base_url="https://share.vyapari.link",
        android_package_name="com.starkinnovations.m360",
    )


def _msg(**over):
    base = {
        "id": "652f00000000000000000001",
        "message_type": "video",
        "text": "Jummah timings changed to 1:30 PM this week.",
        "video_url": "https://stream.mux.com/abc123.m3u8",
        "thumbnail_url": "https://image.mux.com/abc123/thumbnail.jpg",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "masjid_id": "652faaa0000000000000aaaa",
    }
    base.update(over)
    return base


def _masjid(**over):
    base = {
        "name": "Masjid Al Noor",
        "city": "Moradabad",
        "state": "UP",
        "address": "Civil Lines",
        "photo_url": "https://cdn.example/mn.jpg",
        "place_id": "ChIJxxxx",
        "management": {"is_claimed": True},
    }
    base.update(over)
    return base


def test_video_context(settings):
    ctx = build_share_context(_msg(), _masjid(), settings)
    assert ctx["masjid_name"] == "Masjid Al Noor"
    assert ctx["masjid_location"] == "Moradabad, UP"
    assert ctx["masjid_verified"] is True
    assert ctx["is_video"] is True
    assert ctx["video_hls_url"] == "https://stream.mux.com/abc123.m3u8"
    assert ctx["og_image_url"] == (
        "https://image.mux.com/abc123/thumbnail.jpg"
        "?width=1200&height=630&fit_mode=smartcrop"
    )
    assert ctx["og_description"] == "Jummah timings changed to 1:30 PM this week."
    assert ctx["canonical_url"] == (
        "https://share.vyapari.link/s/652f00000000000000000001"
    )
    assert ctx["deep_link_path"] == "/s/652f00000000000000000001"
    assert ctx["share_host"] == "share.vyapari.link"


def test_fallbacks(settings):
    ctx = build_share_context(
        _msg(text=None, thumbnail_url=None),
        _masjid(state="", management={}),
        settings,
    )
    assert ctx["masjid_verified"] is False
    assert ctx["masjid_location"] == "Moradabad"
    assert ctx["og_description"] == "New announcement from Masjid Al Noor"
    assert ctx["og_image_url"].endswith("/share-static/og-default.png")


def test_non_mux_thumbnail_not_resized(settings):
    ctx = build_share_context(
        _msg(thumbnail_url="https://cdn.example/custom.jpg"), _masjid(), settings
    )
    assert ctx["og_image_url"] == "https://cdn.example/custom.jpg"


def test_relative_time_hours(settings):
    from datetime import timedelta

    created = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    ctx = build_share_context(_msg(created_at=created), _masjid(), settings)
    assert ctx["relative_time"] == "2 hrs ago"
