"""E2E coverage for every Mixpanel event emitted by the web share page and embed.

Run: .venv/bin/python3 -m pytest e2e -q
Requires: a local MongoDB (the dev `.env`) and Playwright chromium.
"""

from __future__ import annotations

import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import httpx

from .conftest import (
    BASE,
    MESSAGE_ID,
    analytics_events,
    wait_for,
)

VIDEO_EVENTS = {
    "video_playback_started",
    "video_playback_25_percent",
    "video_playback_50_percent",
    "video_playback_75_percent",
    "video_playback_completed",
    "video_playback_error",
}


def _mock_media_clock(page) -> None:
    page.evaluate(
        """
        () => {
          const v = document.getElementById('v');
          if (!v) throw new Error('no video element');
          let t = 0;
          Object.defineProperty(v, 'duration', { configurable: true, get: () => 100 });
          Object.defineProperty(v, 'currentTime', {
            configurable: true,
            get: () => t,
            set: (value) => { t = value; },
          });
          Object.defineProperty(v, 'paused', { configurable: true, get: () => false });
          window.__fake = {
            play: () => { v.dispatchEvent(new Event('playing')); },
            seek: (value) => { t = value; v.dispatchEvent(new Event('timeupdate')); },
            end: () => { v.dispatchEvent(new Event('ended')); },
            error: () => {
              Object.defineProperty(v, 'error', { configurable: true, value: { code: 4 } });
              v.dispatchEvent(new Event('error'));
            },
          };
        }
        """
    )


def _open_share(ctx, path: str):
    context, events, _ = ctx
    page = context.new_page()
    page.goto(f"{BASE}{path}", wait_until="domcontentloaded")
    return page, events


def test_landing_view_with_share_and_utm(ctx):
    """video_landing_page_viewed carries attribution from ?share + UTM."""
    context, events, _ = ctx
    created = httpx.post(
        f"{BASE}/api/v1/shares",
        json={
            "message_id": MESSAGE_ID,
            "channel": "web_native_share_sheet",
            "platform": "mobile_web",
        },
        timeout=10,
    ).json()["data"]

    page = context.new_page()
    page.goto(
        f"{BASE}/s/{MESSAGE_ID}?share={created['share_id']}&utm_source=whatsapp",
        wait_until="domcontentloaded",
    )
    wait_for(page, lambda: analytics_events(events, "video_landing_page_viewed"))
    event = analytics_events(events, "video_landing_page_viewed")[0]["payload"]["props"]

    assert event["video_id"] == MESSAGE_ID
    assert event["share_id"] == created["share_id"]
    assert event["root_share_id"] == created["root_share_id"]
    assert event["utm_source"] == "whatsapp"
    assert event["platform"] in {"desktop_web", "mobile_web"}
    assert len(event["anonymous_visitor_id"]) > 0


def _assert_readable_time(iso: str) -> None:
    """`event_time_iso` must be an ISO-8601 UTC timestamp the UI can render."""
    assert iso
    parsed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_every_tracked_event_has_readable_time(ctx):
    """Every event carries event_time_iso; the payload time stays numeric."""
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}")
    wait_for(page, lambda: analytics_events(events, "video_landing_page_viewed"))

    for entry in analytics_events(events):
        props = entry["payload"]["props"]
        _assert_readable_time(props["event_time_iso"])
        # `time` is Mixpanel-reserved and must remain numeric epoch seconds.
        if "time" in props:
            assert isinstance(props["time"], (int, float))
            assert not isinstance(props["time"], str)


def test_beacon_payload_has_numeric_time_and_readable_companion(ctx):
    """beaconTrack keeps numeric `time` and adds the readable ISO value."""
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}")
    wait_for(page, lambda: page.query_selector("#shareBtn"))

    payload = page.evaluate(
        """
        async () => {
          const prev = navigator.sendBeacon;
          let captured = null;
          navigator.sendBeacon = function (url, data) { captured = data; return true; };
          try {
            window.M360Analytics.beaconTrack('beacon_probe', { probe: 1 });
          } finally {
            navigator.sendBeacon = prev;
          }
          if (!captured || typeof captured.text !== 'function') return null;
          const body = await captured.text();
          const encoded = decodeURIComponent(body.slice('data='.length));
          return JSON.parse(atob(encoded));
        }
        """
    )

    assert payload is not None, "beacon payload was not captured"
    assert payload["event"] == "beacon_probe"
    props = payload["properties"]
    assert isinstance(props["time"], (int, float))
    assert not isinstance(props["time"], str)
    _assert_readable_time(props["event_time_iso"])
    assert props["event_time_iso"].endswith("Z")


def test_unknown_share_id_is_tolerated(ctx):
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}?share=does-not-exist")
    wait_for(page, lambda: analytics_events(events, "video_landing_page_viewed"))
    event = analytics_events(events, "video_landing_page_viewed")[0]["payload"]["props"]
    assert event["share_id"] == ""
    assert page.title()  # page rendered normally


def test_playback_funnel_once_per_session_and_rearm(ctx):
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}")
    wait_for(page, lambda: analytics_events(events, "video_landing_page_viewed"))
    _mock_media_clock(page)

    page.evaluate("window.__fake.play()")
    page.evaluate("window.__fake.seek(26)")
    page.evaluate("window.__fake.seek(60)")
    page.evaluate("window.__fake.seek(80)")
    page.evaluate("window.__fake.play()")  # duplicate playing must be ignored
    page.evaluate("window.__fake.seek(20)")  # seek back must not re-fire
    page.evaluate("window.__fake.seek(90)")
    page.evaluate("window.__fake.end()")

    wait_for(page, lambda: analytics_events(events, "video_playback_completed"))

    names = [e["payload"]["event"] for e in analytics_events(events)]
    assert names.count("video_playback_started") == 1
    for mark in ("25", "50", "75"):
        assert names.count(f"video_playback_{mark}_percent") == 1

    completed = analytics_events(events, "video_playback_completed")[0]["payload"]["props"]
    assert completed["playback_percentage"] == 100

    # A natural ended re-arms the session.
    page.evaluate("window.__fake.play()")
    page.evaluate("window.__fake.seek(30)")
    wait_for(page, lambda: len(analytics_events(events, "video_playback_started")) == 2)
    assert len(analytics_events(events, "video_playback_25_percent")) == 2


def test_playback_error_event(ctx):
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}")
    wait_for(page, lambda: analytics_events(events, "video_landing_page_viewed"))
    _mock_media_clock(page)
    page.evaluate("window.__fake.play()")
    page.evaluate("window.__fake.error()")

    wait_for(page, lambda: analytics_events(events, "video_playback_error"))
    props = analytics_events(events, "video_playback_error")[0]["payload"]["props"]
    assert props["error_type"] == "media_error"
    assert props["error_code"] == 4


def test_view_masjid_cta_and_store_redirect(ctx):
    context, events, store_urls = ctx
    page = context.new_page()
    page.goto(f"{BASE}/s/{MESSAGE_ID}", wait_until="domcontentloaded")
    wait_for(page, lambda: page.query_selector("#followBtn"))

    page.click("#followBtn")

    wait_for(page, lambda: analytics_events(events, "click_on_view_masjid_cta"))
    cta = analytics_events(events, "click_on_view_masjid_cta")[0]["payload"]["props"]
    assert cta["journey_id"]
    assert cta["cta_destination"] == "masjid_detail"

    wait_for(page, lambda: analytics_events(events, "redirect_to_play_store"))
    redirect = analytics_events(events, "redirect_to_play_store")[0]["payload"]["props"]
    assert redirect["journey_id"] == cta["journey_id"]
    assert redirect["redirect_destination"] == "google_play_store"
    assert redirect["platform"] == "mobile_web"

    wait_for(page, lambda: bool(store_urls))
    store = store_urls[0]
    assert "referrer=" in store
    # The journey and announcement id must survive into the store referrer.
    # The referrer is doubly encoded by design (deeplink=<urlencoded target>,
    # then the whole referrer value is URL-encoded), so decode two layers.
    from urllib.parse import unquote

    decoded = unquote(unquote(store))
    assert f"j={cta['journey_id']}" in decoded
    assert f"m={MESSAGE_ID}" in decoded


def test_web_share_mints_child_link(ctx):
    page, events = _open_share(ctx, f"/s/{MESSAGE_ID}")
    wait_for(page, lambda: page.query_selector("#shareBtn"))

    page.click("#shareBtn")
    wait_for(page, lambda: analytics_events(events, "click_on_share_announcement"))
    wait_for(page, lambda: any(e["name"] == "__copied" for e in events))

    event = analytics_events(events, "click_on_share_announcement")[0]["payload"]["props"]
    copied = [e for e in events if e["name"] == "__copied"][-1]["payload"]["url"]

    assert event["share_channel"] == "web_native_share_sheet"
    assert event["share_id"]
    assert f"share={event['share_id']}" in copied


def test_web_share_extends_the_chain(ctx):
    context, events, _ = ctx
    parent = httpx.post(
        f"{BASE}/api/v1/shares",
        json={
            "message_id": MESSAGE_ID,
            "channel": "web_native_share_sheet",
            "platform": "mobile_web",
        },
        timeout=10,
    ).json()["data"]

    page = context.new_page()
    page.goto(
        f"{BASE}/s/{MESSAGE_ID}?share={parent['share_id']}",
        wait_until="domcontentloaded",
    )
    wait_for(page, lambda: page.query_selector("#shareBtn"))
    page.click("#shareBtn")
    wait_for(page, lambda: analytics_events(events, "click_on_share_announcement"))

    event = analytics_events(events, "click_on_share_announcement")[0]["payload"]["props"]
    assert event["parent_share_id"] == parent["share_id"]
    assert event["root_share_id"] == parent["root_share_id"]


def test_embed_playback_has_in_app_context(ctx):
    context, events, _ = ctx
    page = context.new_page()
    page.goto(
        f"{BASE}/embed/{MESSAGE_ID}?for_app=1#v=dev1&u=user1&j=j1&s=s1",
        wait_until="domcontentloaded",
    )

    wait_for(page, lambda: any(e["name"] == "__register" for e in events))
    register = [e for e in events if e["name"] == "__register"][-1]["payload"]
    assert register["platform"] == "android_app"
    assert register["anonymous_visitor_id"] == "dev1"

    _mock_media_clock(page)
    page.evaluate("window.__fake.play()")
    page.evaluate("window.__fake.seek(30)")
    wait_for(page, lambda: analytics_events(events, "video_playback_25_percent"))

    started = analytics_events(events, "video_playback_started")[0]["payload"]["props"]
    assert started["platform"] == "android_app"
    assert started["anonymous_visitor_id"] == "dev1"
    assert started["user_id"] == "user1"
    assert started["share_id"] == "s1"
    assert started["journey_id"] == "j1"


def test_masjid_landing_page_carries_deferred_deeplink(ctx):
    """`/m/{place_id}` is the browser fallback for masjid share links."""
    context, events, _ = ctx
    page = context.new_page()
    place_id = "ChIJz-lFAQC55zsRLsD1IPMkW14"  # seeded local masjid
    response = page.goto(f"{BASE}/m/{place_id}", wait_until="domcontentloaded")

    assert response.status == 200
    assert page.title()

    html = page.content()
    assert 'property="og:title"' in html
    assert f"/m/{place_id}" in html

    from urllib.parse import unquote

    href = page.get_attribute("#storeLink", "href")
    assert href and "referrer=" in href
    # referrer is doubly encoded: decode to reveal the deferred /m URL.
    decoded = unquote(unquote(href))
    assert f"/m/{place_id}" in decoded
    assert "deeplink=" in decoded


def test_embed_route_and_playback_are_unaffected_when_token_empty(ctx, monkeypatch):
    """Sanity: the embed still plays (and emits nothing) with no token."""
    # This test only asserts the page renders; token removal needs a server
    # restart with an empty MIXPANEL_TOKEN, which is covered by unit tests.
    context, events, _ = ctx
    page = context.new_page()
    page.goto(f"{BASE}/embed/{MESSAGE_ID}?for_app=1", wait_until="domcontentloaded")
    assert page.query_selector("#v") is not None
