# Mux Data Video Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Instrument the public share page and the Flutter app with Mux Data so views/metrics populate in the Mux dashboard.

**Architecture:** Backend adds Mux Data metadata to the share context, calls `mux.monitor` in the existing web player, and serves a minimal `/embed/{id}` page for the app. The Flutter app replaces the native video player with a WebView loading that embed page.

**Tech Stack:** FastAPI + Jinja2 + mux-embed (hls.js integration); Flutter + `webview_flutter`.

## Global Constraints

- `video_id` = Mux playback id; `video_title` = "<masjid> announcement"; `sub_property_id` = place id; `video_stream_type` = `on-demand`; `env_key` = `MUX_ENV_KEY`.
- `player_name`: `m360-share-page` (web) / `m360-app` (embed).
- Guard all Mux calls with `typeof mux !== 'undefined'`; never break playback if the SDK fails.
- `/s/{id}` and `/embed/{id}` must preserve the existing expired/unavailable gating.
- Do not push without explicit instruction.
- Backend tests: `.venv/bin/python -m pytest -q`. Flutter: `flutter analyze`, `flutter test`.

---

## Task 1: Backend — share context + web player instrumentation

**Files:**
- Modify: `app/web/share_context.py`
- Modify: `app/web/templates/share.html`
- Test: `tests/test_share_context.py`, `tests/test_share_template.py`

**Interfaces:**
- Produces context fields: `mux_env_key: str`, `mux_playback_id: str | None`, `analytics_title: str`, `analytics_sub_property_id: str`.

- [ ] **Step 1: Write failing tests**

In `tests/test_share_context.py`:
```python
def test_mux_analytics_fields():
    msg = {
        "id": "m1", "text": "S", "created_at": "2026-10-13T10:00:00+00:00",
        "mux_playback_id": "pb123", "masjid_id": "place1",
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["mux_playback_id"] == "pb123"
    assert ctx["mux_env_key"] == _settings().mux_env_key
    assert ctx["analytics_title"] == "Masjid Al Noor announcement"
    assert ctx["analytics_sub_property_id"] == "place1"
```
(Add `masjid_id` handling: the context should use `message.get("masjid_id")`.)

In `tests/test_share_template.py`, add `mux_env_key="env-1", mux_playback_id="pb1", analytics_title="t", analytics_sub_property_id="p"` to `_render`, then:
```python
def test_share_page_instruments_mux_data():
    html = _render()
    assert "src.litix.io/core/4/mux.js" in html
    assert "mux.monitor" in html
    assert '"env-1"' in html and '"pb1"' in html
```

- [ ] **Step 2: Run to fail** → `.venv/bin/python -m pytest tests/test_share_context.py tests/test_share_template.py -q` (FAIL).

- [ ] **Step 3: Implement context** — in `share_context.py`, add before `return`:
```python
    mux_playback_id = message.get("mux_playback_id") or None
    analytics_title = f"{name} announcement"
    analytics_sub_property_id = str(message.get("masjid_id") or "")
```
and to the dict:
```python
        "mux_env_key": settings.mux_env_key,
        "mux_playback_id": mux_playback_id,
        "analytics_title": analytics_title,
        "analytics_sub_property_id": analytics_sub_property_id,
```

- [ ] **Step 4: Instrument `share.html`**

Add in `<head>`:
```html
<script src="https://src.litix.io/core/4/mux.js"></script>
```
In the script block:
```js
  var MUX_ENV_KEY = {{ mux_env_key | tojson }};
  var MUX_PLAYBACK_ID = {{ (mux_playback_id or "") | tojson }};
  var ANALYTICS_TITLE = {{ analytics_title | tojson }};
  var ANALYTICS_SUB_PROPERTY = {{ analytics_sub_property_id | tojson }};
  var PLAYER_NAME = "m360-share-page";
  var MUX_INIT_TIME = (typeof mux !== "undefined") ? mux.utils.now() : Date.now();

  function startMux(videoEl, hlsInstance) {
    if (typeof mux === "undefined") return;
    var opts = {
      data: {
        env_key: MUX_ENV_KEY,
        player_name: PLAYER_NAME,
        player_init_time: MUX_INIT_TIME,
        video_id: MUX_PLAYBACK_ID || undefined,
        video_title: ANALYTICS_TITLE,
        sub_property_id: ANALYTICS_SUB_PROPERTY,
        video_stream_type: "on-demand",
      },
    };
    if (hlsInstance) { opts.hlsjs = hlsInstance; opts.Hls = window.Hls; }
    try { mux.monitor(videoEl, opts); } catch (e) {}
  }
```
Call `startMux(v, hls)` after `hls.attachMedia(v)`, and `startMux(v)` in the native-HLS branch (before/after `v.src = HLS_URL`).

- [ ] **Step 5: Run tests** → PASS.

- [ ] **Step 6: Commit** — `feat(share): instrument share page with Mux Data`.

---

## Task 2: Backend — `/embed/{id}` player page

**Files:**
- Modify: `app/web/share.py`
- Create: `app/web/templates/share_embed.html`
- Create: `app/web/templates/_share_player.html` (shared player JS)
- Test: `tests/test_share_template.py`

- [ ] **Step 1: Create `share_embed.html`** — minimal black page:
```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{ page_title }}</title>
<script src="https://src.litix.io/core/4/mux.js"></script>
<style>
  html,body{margin:0;height:100%;background:#000}
  video{width:100%;height:100%;object-fit:contain;background:#000}
</style>
</head><body>
<video id="v" controls playsinline preload="metadata"
  {% if poster_url %}poster="{{ poster_url }}"{% endif %}></video>
{% set player_name = "m360-app" %}
{% include "_share_player.html" %}
</body></html>
```

- [ ] **Step 2: Create `_share_player.html`** — the HLS + Mux monitoring JS, using `HLS_URL`, `MUX_*`, and `player_name` from the context (same logic as Task 1, but with `player_name` variable). It must work when `#play` is absent.

- [ ] **Step 3: Add the route** in `share.py`:
```python
@router.get("/embed/{message_id}", response_class=HTMLResponse)
def embed_page(message_id: str, request: Request, settings: Settings = Depends(get_settings),
               feed_svc=Depends(get_broadcast_feed_service),
               masjid_svc=Depends(get_masjid_entity_service)) -> HTMLResponse:
    try:
        message = feed_svc.get_message_raw(message_id)
        masjid = (masjid_svc.get_masjid(message["masjid_id"]) or {}).get("masjid", {})
    except Exception:
        return HTMLResponse("<html><body>Not found</body></html>", status_code=404)
    if resolve_share_state(message) in {"unavailable", "expired"}:
        return HTMLResponse("<html><body>Not available</body></html>", status_code=404)
    ctx = build_share_context(message, masjid, settings)
    html = env.get_template("share_embed.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "no-store"
    return resp
```

- [ ] **Step 4: Tests** — render `share_embed.html` with the same context and assert `mux.monitor`, `<video`, and that the embed route 404s for an expired/unavailable message (unit-test `resolve_share_state` already covers the state; a route test is optional).

- [ ] **Step 5: Run tests** → PASS.

- [ ] **Step 6: Commit** — `feat(share): add /embed/{id} player page for app Mux Data`.

---

## Task 3: Flutter — WebView player

**Files:**
- Modify: `pubspec.yaml` (add `webview_flutter`)
- Modify: `lib/features/home/widgets/broadcast_video_player.dart`
- Modify: `lib/features/home/widgets/broadcast_message_card.dart:551`
- Test: `test/broadcast_video_player_test.dart` (new)

- [ ] **Step 1: Add dependency** `webview_flutter: ^4.10.0`; run `flutter pub get`.

- [ ] **Step 2: Add a pure URL helper** (testable):
```dart
String buildEmbedUrl(String apiBaseUrl, String messageId) {
  var origin = apiBaseUrl.trim();
  final idx = origin.indexOf('/api/');
  if (idx >= 0) origin = origin.substring(0, idx);
  origin = origin.replaceAll(RegExp(r'/+$'), '');
  return '$origin/embed/$messageId';
}
```
Put it in `broadcast_video_player.dart` (top-level).

- [ ] **Step 3: Rewrite `BroadcastVideoPlayer`** to take `required String messageId`, build the URL from `dotenv.env['API_BASE_URL']`, and render:
```dart
final controller = WebViewController()
  ..setJavaScriptMode(JavaScriptMode.unrestricted)
  ..loadRequest(Uri.parse(url));
```
For Android, `if (controller.platform is AndroidWebViewController) { (controller.platform as AndroidWebViewController).setMediaPlaybackRequiresUserGesture(false); }`. Render `WebViewWidget(controller: controller)` in a black `Scaffold`.

- [ ] **Step 4: Update the call site** in `broadcast_message_card.dart` to pass `messageId: widget.messageId`.

- [ ] **Step 5: Test** — `buildEmbedUrl('https://muslim360.in/api/v1', 'm1') == 'https://muslim360.in/embed/m1'`; `flutter analyze`; `flutter test`.

- [ ] **Step 6: Commit** — `feat(app): play announcements via WebView embed for Mux Data`.

---

## Verification

- [ ] Backend suite green.
- [ ] Flutter analyze/tests green.
- [ ] On the share page, play a video; within ~1–2 min the Mux dashboard shows a view (filter by `player_name=m360-share-page`).
- [ ] In the app, open a video; a view appears with `player_name=m360-app`.
- [ ] Expired/unavailable posts still 404 on embed and show the gated page on `/s`.
