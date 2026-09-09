from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MONGODB_ENABLED", "false")

from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.web.share_context import build_share_context
from app.web.templating import env

HLS_URL = "https://stream.mux.com/abc123.m3u8"


@pytest.fixture
def html() -> str:
    settings = Settings(
        share_web_base_url="https://share.vyapari.link",
        android_package_name="com.starkinnovations.m360",
    )
    message = {
        "id": "652f00000000000000000001",
        "message_type": "video",
        "text": "Jummah timings changed to 1:30 PM this week.",
        "video_url": HLS_URL,
        "thumbnail_url": "https://image.mux.com/abc123/thumbnail.jpg",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "masjid_id": "652faaa0000000000000aaaa",
    }
    masjid = {"name": "Masjid Al Noor", "city": "Hyderabad", "state": "Telangana"}
    ctx = build_share_context(message, masjid, settings)
    return env.get_template("share.html").render(**ctx)


def test_player_uses_mse_detection_not_can_play_type(html: str) -> None:
    """Chromium returns "maybe" for the HLS MIME type but cannot play HLS.

    Gating the player on canPlayType alone sent every Chrome/Edge/Android
    WebView viewer down the native branch, where the .m3u8 fails with
    MEDIA_ERR_SRC_NOT_SUPPORTED and hls.js never loads. MSE presence is the
    signal that actually distinguishes the two players.
    """
    assert "function hasMSE()" in html
    assert "MediaSource.isTypeSupported" in html
    assert "if (!hasMSE()) { native(); return; }" in html
    # The old, broken gate must not come back.
    assert 'if (v.canPlayType("application/vnd.apple.mpegurl")) {' not in html


def test_hidden_attribute_is_forced_over_author_display_rules(html: str) -> None:
    """`.playbtn{display:flex}` outranks the UA `[hidden]{display:none}`,
    so without this rule the play button stayed on top of the video."""
    assert "[hidden]{display:none!important}" in html


def test_player_guards_against_a_second_attach(html: str) -> None:
    assert "if (started) return;" in html


def test_player_restores_poster_on_failure(html: str) -> None:
    """A failed load must not leave a black rectangle the viewer cannot retry."""
    assert "function fail()" in html
    assert "s.onerror" in html
    assert "window.Hls.Events.ERROR" in html


def test_hls_js_is_pinned_with_integrity(html: str) -> None:
    assert "hls.js@1.5.13/dist/hls.min.js" in html
    assert "sha384-w6Gb3fXHb5e1LUYa/hYA5Q41bEDglN5ZPCG7Jvnoo8/X90oGnlPqBlBJCe38mEMm" in html


# --- layout: the page must fit one screen, no scrolling -----------------------


def test_wrap_has_definite_height_so_media_can_shrink(html: str) -> None:
    """`min-height:100vh` let the wrap grow with its content, pushing the card
    and buttons below the fold. A definite dvh height makes the media box the
    flexible one instead."""
    assert "height:100vh;height:100dvh" in html
    assert "min-height:100vh" not in html


def test_media_can_shrink_below_its_content(html: str) -> None:
    """`min-height:60vh` plus the flex auto-minimum kept the media box tall."""
    assert "flex:1 1 auto;min-height:0" in html
    assert "min-height:60vh" not in html


def test_poster_and_video_are_out_of_flow(html: str) -> None:
    """An in-flow img with height:100% against an indefinite parent falls back
    to auto, so its intrinsic height (693px for a 720x1280 thumb at 390px wide)
    dictated the layout."""
    assert ".media video,.media img.poster{position:absolute;inset:0" in html


def test_fixed_sections_do_not_flex(html: str) -> None:
    for rule in (".topbar{flex:0 0 auto", ".card{flex:0 0 auto", ".btns{flex:0 0 auto"):
        assert rule in html, rule


def test_long_announcement_text_is_clamped(html: str) -> None:
    """The wrap is a fixed-height no-scroll box, so unbounded text would push
    the CTA row out of view."""
    assert "-webkit-line-clamp:3" in html
