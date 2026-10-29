import re
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.deps import (
    get_broadcast_feed_service,
    get_masjid_entity_service,
    get_masjid_search_service,
    get_share_service,
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
        caption="Salaam",
        page_title="Masjid Al Noor — announcement | Muslim 360",
        relative_time="2 hrs ago",
        canonical_url="https://muslim360.in/s/m1",
        share_url="https://muslim360.in/s/m1",
        follow_path="/m/place1",
        deep_link_path="/s/m1",
        share_host="muslim360.in",
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        android_package="com.starkinnovations.m360",
        marketing_site_url="https://muslim360.app",
        mux_env_key="env-1",
        video_id="m1",
        share_id="",
        root_share_id="",
        parent_share_id="",
        utm_source="",
        utm_medium="",
        utm_campaign="",
        mixpanel_token="mp-token",
        mixpanel_api_host="https://api.mixpanel.com",
        masjid_place_id="place1",
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
    assert "View Masjid" in html
    assert 'class="applogo"' in html
    assert "/share-static/logo.png" in html
    assert 'id="followBtn"' in html
    assert 'id="shareBtn"' in html
    assert "intent://" in html


def test_text_only_post_shows_announcement_and_no_media():
    html = _render(is_video=False, video_hls_url=None, poster_url=None)
    assert '<p class="caption">Salaam</p>' in html
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


def test_non_video_with_poster_renders_image_and_footer_caption():
    html = _render(
        is_video=False,
        video_hls_url=None,
        poster_url="https://img/p.jpg",
    )
    media = _media_block(html)
    assert '<img class="poster" src="https://img/p.jpg"' in media
    assert '<p class="caption">Salaam</p>' in html
    assert ".caption{" in html


def test_caption_renders_below_sender_row_above_ctas():
    html = _render()
    assert '<p class="caption">Salaam</p>' in html
    assert html.index('class="srow"') < html.index('class="caption"')
    assert html.index('class="caption"') < html.index('class="ctas"')


def test_share_template_builds_journey_link():
    html = _render()
    assert "journey_id" in html
    assert "click_on_view_masjid_cta" in html


def _script_function(html: str, name: str) -> str:
    match = re.search(
        r"function %s\([^)]*\) \{.*?\n  \}" % re.escape(name), html, re.S
    )
    assert match, f"function {name} not found"
    return match.group(0)


def test_share_template_renders_share_id_for_cta():
    html = _render(share_id="s1")
    assert 'var SHARE_ID = "s1"' in html


def test_follow_url_carries_journey_and_share_id():
    html = _render(share_id="s1")
    follow = _script_function(html, "followUrl")
    assert '"j=" + encodeURIComponent(journey)' in follow
    assert 'params.push("s=" + encodeURIComponent(SHARE_ID))' in follow
    assert '"?" + params.join("&")' in follow


def test_open_app_store_fallback_uses_per_click_url():
    html = _render()
    open_app = _script_function(html, "openApp")
    assert "storeUrlFor(targetUrl)" in open_app


def test_share_cta_uses_muslim360_base_url():
    html = _render()
    line = next(l for l in html.splitlines() if "var PAGE_URL" in l)
    assert "https://muslim360.in/s/m1" in line


def test_share_template_creates_child_share_and_tracks_redirect():
    html = _render()
    assert "click_on_share_announcement" in html
    assert "redirect_to_play_store" in html
    assert "/api/v1/shares" in html


def test_share_template_includes_analytics_bootstrap():
    html = _render(mixpanel_token="mp-token")
    assert "M360_ANALYTICS_BASE" in html
    assert "m360-analytics.js" in html
    assert "video_landing_page_viewed" in html
    assert html.index("M360_ANALYTICS_BASE") > html.index("var IS_ANDROID")
    assert "M360Analytics.setupPlayer" in html
    assert 'IS_ANDROID ? "mobile_web"' in html


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


class _SearchService:
    def get_place_by_id(self, _place_id):
        return {}


def _share_client(message=None, masjid=None, share_svc=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: Settings(
        share_web_base_url="https://muslim360.in",
        android_package_name="com.starkinnovations.m360",
        mux_env_key="env-1",
    )
    app.dependency_overrides[get_broadcast_feed_service] = lambda: _FeedService(
        message, None
    )
    app.dependency_overrides[get_masjid_entity_service] = lambda: _MasjidService(
        masjid
    )
    app.dependency_overrides[get_masjid_search_service] = lambda: _SearchService()
    app.dependency_overrides[get_share_service] = lambda: share_svc
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


def test_follow_cta_uses_masjid_deep_link():
    html = _render()
    line = next(l for l in html.splitlines() if "var FOLLOW_PATH" in l)
    assert '"/m/place1"' in line
    intent = next(l for l in html.splitlines() if "intent://" in l)
    assert "FOLLOW_PATH" in intent


def test_area_and_city_skips_generic_sublocality():
    from app.web.share import _area_and_city
    place = {"addressComponents": [
        {"longText": "City", "types": ["sublocality_level_1", "sublocality"]},
        {"longText": "Civil Lines", "types": ["sublocality_level_2", "sublocality"]},
        {"longText": "Aligarh", "types": ["locality", "political"]},
    ]}
    assert _area_and_city(place) == ("Civil Lines", "Aligarh")


def test_area_and_city_falls_back_to_city_only_when_area_generic():
    from app.web.share import _area_and_city
    place = {"addressComponents": [
        {"longText": "City", "types": ["sublocality_level_1", "sublocality"]},
        {"longText": "Aligarh", "types": ["locality", "political"]},
    ]}
    assert _area_and_city(place) == ("", "Aligarh")


def test_follow_button_hidden_without_place_id():
    html = _render(follow_path="")
    assert "View Masjid" not in html
    assert 'id="followBtn"' not in html
    assert 'id="shareBtn"' in html


def test_embed_route_allows_in_app_playback_when_sharing_disabled():
    client = _embed_client(
        message=_video_message(allow_sharing=False),
        masjid={"name": "Masjid Al Noor"},
    )
    resp = client.get("/embed/m1?for_app=1")
    assert resp.status_code == 200
    assert "<video" in resp.text


def test_embed_route_allows_in_app_playback_when_expired():
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    client = _embed_client(
        message=_video_message(expires_at=expired),
        masjid={"name": "Masjid Al Noor"},
    )
    resp = client.get("/embed/m1?for_app=1")
    assert resp.status_code == 200


def test_share_page_tolerates_unknown_share_id():
    client = _share_client(
        message=_video_message(), masjid={"name": "Masjid Al Noor"}, share_svc=None
    )
    resp = client.get("/s/m1?share=does-not-exist")
    assert resp.status_code == 200
    assert "Masjid Al Noor" in resp.text


def _request(query: str = ""):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/s/m1",
            "query_string": query.encode(),
            "headers": [],
        }
    )


class _ShareServiceStub:
    def __init__(self, record=None, error=None):
        self._record = record
        self._error = error

    def get_share(self, share_id):
        if self._error is not None:
            raise self._error
        return self._record


_EMPTY_ATTRIBUTION = {
    "share_id": "",
    "root_share_id": "",
    "parent_share_id": "",
    "utm_source": "",
    "utm_medium": "",
    "utm_campaign": "",
}


def test_share_attribution_reads_record_and_stored_utms():
    from app.web.share import _share_attribution

    svc = _ShareServiceStub(
        {
            "share_id": "s1",
            "root_share_id": "s0",
            "parent_share_id": "p0",
            "message_id": "m1",
            "utm_source": "whatsapp",
            "utm_medium": "social",
            "utm_campaign": "eid",
        }
    )
    attr = _share_attribution(_request("share=s1"), svc, "m1")
    assert attr == {
        "share_id": "s1",
        "root_share_id": "s0",
        "parent_share_id": "p0",
        "utm_source": "whatsapp",
        "utm_medium": "social",
        "utm_campaign": "eid",
    }


def test_share_attribution_empty_for_unknown_share_id():
    from app.web.share import _share_attribution

    attr = _share_attribution(
        _request("share=does-not-exist"), _ShareServiceStub(None), "m1"
    )
    assert attr == _EMPTY_ATTRIBUTION


def test_share_attribution_swallows_lookup_errors():
    from app.web.share import _share_attribution

    attr = _share_attribution(
        _request("share=s1"), _ShareServiceStub(error=RuntimeError("boom")), "m1"
    )
    assert attr == _EMPTY_ATTRIBUTION


def test_share_attribution_url_utms_win_over_record():
    from app.web.share import _share_attribution

    svc = _ShareServiceStub(
        {
            "share_id": "s1",
            "root_share_id": "s0",
            "parent_share_id": "p0",
            "message_id": "m1",
            "utm_source": "whatsapp",
            "utm_medium": "social",
            "utm_campaign": "eid",
        }
    )
    attr = _share_attribution(
        _request("share=s1&utm_source=telegram&utm_campaign=url-campaign"), svc, "m1"
    )
    assert attr == {
        "share_id": "s1",
        "root_share_id": "s0",
        "parent_share_id": "p0",
        "utm_source": "telegram",
        "utm_medium": "social",
        "utm_campaign": "url-campaign",
    }


def test_share_attribution_ignores_record_for_other_message():
    from app.web.share import _share_attribution

    svc = _ShareServiceStub(
        {
            "share_id": "s1",
            "root_share_id": "s0",
            "parent_share_id": "p0",
            "message_id": "message-A",
            "utm_source": "whatsapp",
            "utm_medium": "social",
            "utm_campaign": "eid",
        }
    )
    attr = _share_attribution(_request("share=s1"), svc, "message-B")
    assert attr == _EMPTY_ATTRIBUTION


def test_share_page_ignores_attribution_from_another_message():
    client = _share_client(
        message=_video_message(),
        masjid={"name": "Masjid Al Noor"},
        share_svc=_ShareServiceStub(
            {"share_id": "s1", "message_id": "message-A"}
        ),
    )
    resp = client.get("/s/m1?share=s1")
    assert resp.status_code == 200
    assert "Masjid Al Noor" in resp.text
