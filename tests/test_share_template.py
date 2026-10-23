from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import (
    get_broadcast_feed_service,
    get_masjid_entity_service,
)
from app.core.config import Settings, get_settings
from app.web.share import router
from app.web.templating import env


def _render(**overrides):
    ctx = dict(
        message_id="m1",
        masjid_name="Masjid Al Noor",
        masjid_location="Thane, Maharashtra",
        masjid_verified=True,
        masjid_avatar_url="https://img/m.jpg",
        sender_name="Najim Ahmed",
        sender_role="Imam",
        sender_avatar_url="https://img/u.jpg",
        is_video=True,
        video_hls_url="https://stream/x.m3u8",
        poster_url="https://img/p.jpg",
        og_image_url="https://img/og.jpg",
        og_description="Salaam",
        page_title="Masjid Al Noor — announcement | Muslim 360",
        relative_time="2 hrs ago",
        canonical_url="https://muslim360.in/s/m1",
        share_url="https://muslim360.in/s/m1",
        deep_link_path="/s/m1",
        share_host="muslim360.in",
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        android_package="com.starkinnovations.m360",
        marketing_site_url="https://muslim360.app",
        mux_env_key="env-1",
        mux_playback_id="pb1",
        analytics_title="t",
        analytics_sub_property_id="p",
    )
    ctx.update(overrides)
    return env.get_template("share.html").render(**ctx)


def test_share_template_renders_new_layout():
    html = _render()
    assert "Masjid Al Noor" in html
    assert "Najim Ahmed" in html
    assert "Imam" in html
    assert "Follow Masjid" in html
    assert 'class="applogo"' in html
    assert "/share-static/logo.png" in html
    assert 'id="followBtn"' in html
    assert 'id="shareBtn"' in html
    assert "intent://" in html


def test_text_only_post_shows_announcement_and_no_media():
    html = _render(is_video=False, video_hls_url=None, poster_url=None)
    assert '<p class="text">Salaam</p>' in html
    assert '<main class="media"' not in html


def test_none_description_does_not_leak_into_page():
    html = _render(og_description=None)
    assert "None" not in html


def test_video_post_renders_media_and_play_control():
    html = _render()
    assert '<main class="media"' in html
    assert 'id="play"' in html


def _media_block(html: str) -> str:
    start = html.index('<main class="media"')
    end = html.index("</main>", start) + len("</main>")
    return html[start:end]


def test_video_without_poster_uses_dark_placeholder_not_og_card():
    html = _render(
        poster_url=None,
        og_image_url="https://muslim360.in/share-static/og-default.png",
    )
    media = _media_block(html)
    assert 'class="poster placeholder"' in media
    assert "og-default.png" not in media
    assert '<img class="poster"' not in media


def test_non_video_with_poster_renders_image_and_caption_below():
    html = _render(
        is_video=False,
        video_hls_url=None,
        poster_url="https://img/p.jpg",
    )
    media = _media_block(html)
    assert '<img class="poster" src="https://img/p.jpg"' in media
    assert '<p class="text">Salaam</p>' in html
    assert html.index('<main class="media"') < html.index('<div class="textwrap')
    assert '<div class="textwrap">' in html
    assert ".textwrap{flex:0 1 auto" in html
    assert ".textwrap.full{flex:1" in html


def test_text_only_post_text_fills_available_space():
    html = _render(is_video=False, video_hls_url=None, poster_url=None)
    assert '<div class="textwrap full">' in html


def test_share_cta_uses_muslim360_base_url():
    html = _render()
    line = next(l for l in html.splitlines() if "var PAGE_URL" in l)
    assert "https://muslim360.in/s/m1" in line


def test_share_page_instruments_mux_data():
    html = _render()
    assert "src.litix.io/core/4/mux.js" in html
    assert "mux.monitor" in html
    assert '"env-1"' in html and '"pb1"' in html


def _embed_context(**overrides):
    ctx = dict(
        page_title="Masjid Al Noor — announcement | Muslim 360",
        poster_url="https://img/p.jpg",
        video_hls_url="https://stream/x.m3u8",
        mux_env_key="env-1",
        mux_playback_id="pb1",
        analytics_title="Masjid Al Noor announcement",
        analytics_sub_property_id="place1",
    )
    ctx.update(overrides)
    return ctx


def test_embed_template_renders_fullscreen_player_with_mux():
    html = env.get_template("share_embed.html").render(**_embed_context())
    assert "<video" in html
    assert 'id="v"' in html
    assert "controls" in html
    assert "src.litix.io/core/4/mux.js" in html
    assert "mux.monitor" in html
    assert '"env-1"' in html and '"pb1"' in html
    assert '"m360-app"' in html
    assert 'id="play"' not in html


def test_embed_template_guards_missing_mux_sdk():
    html = env.get_template("share_embed.html").render(**_embed_context())
    assert 'typeof mux === "undefined"' in html
    assert "try { mux.monitor" in html


class _FeedService:
    def __init__(self, message=None, error=None):
        self._message = message
        self._error = error

    def get_message_raw(self, message_id):
        if self._error is not None:
            raise self._error
        return self._message


class _MasjidService:
    def __init__(self, masjid=None):
        self._masjid = masjid or {}

    def get_masjid(self, masjid_id):
        return {"masjid": self._masjid}


def _embed_client(message=None, masjid=None, error=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: Settings(
        share_web_base_url="https://muslim360.in",
        android_package_name="com.starkinnovations.m360",
        mux_env_key="env-1",
    )
    app.dependency_overrides[get_broadcast_feed_service] = lambda: _FeedService(
        message, error
    )
    app.dependency_overrides[get_masjid_entity_service] = lambda: _MasjidService(
        masjid
    )
    return TestClient(app)


def _video_message(**overrides):
    msg = {
        "id": "m1",
        "masjid_id": "place1",
        "message_type": "video",
        "video_url": "https://stream/x.m3u8",
        "thumbnail_url": "https://img/p.jpg",
        "mux_playback_id": "pb1",
        "text": "Salaam",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    msg.update(overrides)
    return msg


def test_embed_route_renders_player_for_available_message():
    client = _embed_client(
        message=_video_message(), masjid={"name": "Masjid Al Noor"}
    )
    resp = client.get("/embed/m1")
    assert resp.status_code == 200
    assert "mux.monitor" in resp.text
    assert "<video" in resp.text
    assert '"pb1"' in resp.text
    assert '"m360-app"' in resp.text
    assert resp.headers["cache-control"] == "no-store"


def test_embed_route_404s_when_sharing_disabled():
    client = _embed_client(
        message=_video_message(allow_sharing=False),
        masjid={"name": "Masjid Al Noor"},
    )
    resp = client.get("/embed/m1")
    assert resp.status_code == 404
    assert "Not available" in resp.text


def test_embed_route_404s_when_expired():
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    client = _embed_client(
        message=_video_message(expires_at=expired),
        masjid={"name": "Masjid Al Noor"},
    )
    resp = client.get("/embed/m1")
    assert resp.status_code == 404
    assert "Not available" in resp.text


def test_embed_route_404s_on_fetch_error():
    client = _embed_client(error=RuntimeError("boom"))
    resp = client.get("/embed/m1")
    assert resp.status_code == 404
    assert "Not found" in resp.text
