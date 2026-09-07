# Broadcast Share Page + Deep Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw Mux link shared from the app with a branded web page that has rich social previews and deep-links back into the app to the right masjid.

**Architecture:** A server-rendered share page + `.well-known` association files are added to `m360-backend` (`app/web/`). The Flutter app gains an `app_links`-based `DeepLinkService` that resolves an incoming `https://<host>/s/{messageId}` link to a masjid and builds the navigation stack (masjid list → masjid detail → optionally the broadcast feed). The three in-app share call-sites switch from sharing the video URL to sharing the new page URL.

**Tech Stack:** FastAPI + Jinja2 + pydantic-settings (backend); Flutter + `app_links` + Provider + Dio (app); hls.js (CDN) on the web page.

**Spec:** `m360-backend/docs/superpowers/specs/2026-09-07-broadcast-share-deeplink-design.md`

## Global Constraints

- **Two repos, two branches.** Backend work → `m360-backend` on branch `feat/broadcast-share-deeplink` (off `origin/main`). App work → `m360-flutter-app` on branch `feat/broadcast-share-deeplink` (off `origin/v3`). Commits go to whichever repo the task's files live in.
- **Backend Python:** follow existing style — `from __future__ import annotations`, type hints, no new heavyweight deps. Jinja2 `Environment` is already a dependency. Tests use `fastapi.testclient.TestClient` + `pytest`, env vars set via `os.environ` **before** app imports (see `tests/test_web_admin_router.py`).
- **Backend config:** every new setting lives in `app/core/config.py` `Settings` with a safe default so the app boots with nothing configured. `get_settings()` is `@lru_cache`'d — tests call `get_settings.cache_clear()`.
- **Backend response envelope:** JSON API responses use `success_response(data, message, status_code)` → `{"status","message","data"}`.
- **App id:** `com.starkinnovations.m360` (Android `applicationId` + iOS `PRODUCT_BUNDLE_IDENTIFIER`, both platforms).
- **App Dart:** Dart 3.6+. No new state management (Provider only). All HTTP via `ApiService` (Dio wrapper). Every user-visible string gets an ARB key in `lib/l10n/app_en.arb` + `app_hi.arb`, then `flutter gen-l10n`. Navigation via named routes / `NavigationService.navigatorKey`.
- **Share host placeholder:** use `share.vyapari.link` everywhere a literal host is needed until the owner provides the final subdomain. It is read from config/env, never hard-coded in logic.
- **Deep-link path shape:** `/s/{messageId}` where `messageId` matches `^[A-Za-z0-9_-]+$` (Mongo ObjectId hex in practice, but keep the charset permissive).
- **Best-effort deep linking only:** no deferred deep link. App-not-installed → store → normal home screen.
- **Feed gate respected:** a deep link for a masjid the user has not followed lands on the **masjid detail page**, not the feed.

---

## Phase 1 — Backend (`m360-backend`)

### Task 1: Config + `.well-known` association endpoints

**Files:**
- Modify: `app/core/config.py` (add settings to `Settings`, after the `mux_*` block ~line 150)
- Create: `app/web/share.py`
- Modify: `app/factory.py:67-78` (mount share router + static, unconditionally)
- Test: `tests/test_share_wellknown.py`

**Interfaces:**
- Produces:
  - `Settings.share_web_base_url: str`, `.share_host: str` (property — host of `share_web_base_url`), `.android_package_name: str`, `.android_sha256_cert_fingerprints: list[str]`, `.apple_team_id: str`, `.apple_bundle_id: str`, `.apple_app_id: str` (property — `f"{team_id}.{bundle_id}"`), `.play_store_url: str`, `.app_store_url: str`, `.marketing_site_url: str`
  - `app/web/share.py::router` — `APIRouter()` (no prefix)
  - `GET /.well-known/assetlinks.json` → `JSONResponse` (list)
  - `GET /.well-known/apple-app-site-association` → `Response(media_type="application/json")`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_wellknown.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd m360-backend && .venv/bin/pytest tests/test_share_wellknown.py -v`
Expected: FAIL — `ModuleNotFoundError: app.web.share`

- [ ] **Step 3: Add settings to `app/core/config.py`**

Add inside `class Settings` (after the `mux_env_key` line, before `rate_limit_enabled`):

```python
    share_web_base_url: str = Field(
        default="https://share.vyapari.link",
        validation_alias=AliasChoices("SHARE_WEB_BASE_URL", "share_web_base_url"),
    )
    android_package_name: str = "com.starkinnovations.m360"
    android_sha256_cert_fingerprints_raw: str = Field(
        default="",
        validation_alias=AliasChoices(
            "ANDROID_SHA256_CERT_FINGERPRINTS",
            "android_sha256_cert_fingerprints_raw",
        ),
    )
    apple_team_id: str = Field(
        default="", validation_alias=AliasChoices("APPLE_TEAM_ID", "apple_team_id")
    )
    apple_bundle_id: str = "com.starkinnovations.m360"
    play_store_url: str = (
        "https://play.google.com/store/apps/details?id=com.starkinnovations.m360"
    )
    app_store_url: str = "https://apps.apple.com/app/muslim-360/id6608000000"
    marketing_site_url: str = "https://muslim360.app"
```

And add these properties (near the other `@property` defs):

```python
    @property
    def share_host(self) -> str:
        from urllib.parse import urlparse

        return urlparse(self.share_web_base_url).netloc or self.share_web_base_url

    @property
    def android_sha256_cert_fingerprints(self) -> list[str]:
        return [
            f.strip()
            for f in self.android_sha256_cert_fingerprints_raw.split(",")
            if f.strip()
        ]

    @property
    def apple_app_id(self) -> str:
        return f"{self.apple_team_id}.{self.apple_bundle_id}" if self.apple_team_id else ""
```

- [ ] **Step 4: Create `app/web/share.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.api.deps import get_broadcast_feed_service, get_masjid_entity_service
from app.core.config import Settings, get_settings

router = APIRouter(tags=["share"])


@router.get("/.well-known/assetlinks.json")
def assetlinks(settings: Settings = Depends(get_settings)) -> JSONResponse:
    return JSONResponse(
        content=[
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": settings.android_package_name,
                    "sha256_cert_fingerprints": settings.android_sha256_cert_fingerprints,
                },
            }
        ]
    )


@router.get("/.well-known/apple-app-site-association")
def apple_app_site_association(settings: Settings = Depends(get_settings)) -> Response:
    import json

    payload = {
        "applinks": {
            "apps": [],
            "details": [{"appID": settings.apple_app_id, "paths": ["/s/*"]}],
        }
    }
    return Response(content=json.dumps(payload), media_type="application/json")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_share_wellknown.py -v`
Expected: PASS (both tests)

- [ ] **Step 6: Wire into `app/factory.py`**

After `application.include_router(api_v1_router, prefix="/api/v1")` (line 67), add — **outside** the `if settings.admin_panel_enabled:` block:

```python
    from fastapi.staticfiles import StaticFiles as _ShareStatic
    from app.web.share import router as share_router

    application.mount(
        "/share-static",
        _ShareStatic(directory="app/web/static"),
        name="share_static",
    )
    application.include_router(share_router)
```

- [ ] **Step 7: Run the full web test suite + boot check**

Run: `.venv/bin/pytest tests/test_share_wellknown.py tests/test_web_admin_router.py -v`
Run: `.venv/bin/python -c "from app.factory import create_app; create_app()"`
Expected: tests PASS, app constructs with no exception

- [ ] **Step 8: Commit**

```bash
cd m360-backend
git add app/core/config.py app/web/share.py app/factory.py tests/test_share_wellknown.py
git commit -m "feat(share): config + App Links / Universal Links association files

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AEubAUb6psgKtPEMaDW13Z"
```

---

### Task 2: `SharePageContext` builder

**Files:**
- Create: `app/web/share_context.py`
- Test: `tests/test_share_context.py`

**Interfaces:**
- Consumes: raw message dict (shape from `BroadcastFeedService.get_message_raw` — keys `id`, `message_type`, `text`, `video_url`, `thumbnail_url`, `created_at`, `masjid_id`), raw masjid dict (`MasjidEntityService.get_masjid(...)["masjid"]` — keys `name`, `city`, `state`, `address`, `photo_url`, `place_id`, `management.is_claimed`), and `Settings`.
- Produces: `build_share_context(message: dict, masjid: dict, settings: Settings) -> dict` with keys:
  `message_id, masjid_name, masjid_location, masjid_verified (bool), masjid_avatar_url, is_video (bool), video_hls_url (str|None), poster_url (str|None), og_image_url (str), og_description (str), page_title, relative_time (str), canonical_url, deep_link_path, share_host, play_store_url, app_store_url, android_package, marketing_site_url`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_context.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_share_context.py -v`
Expected: FAIL — `ModuleNotFoundError: app.web.share_context`

- [ ] **Step 3: Create `app/web/share_context.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import Settings

_OG_DESC_MAX = 200


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _relative_time(created_at: Any) -> str:
    dt = _parse_dt(created_at)
    if dt is None:
        return ""
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr ago" if hrs == 1 else f"{hrs} hrs ago"
    days = hrs // 24
    if days < 7:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} wk ago" if weeks == 1 else f"{weeks} wks ago"
    return dt.strftime("%d %b %Y")


def _sized_og_image(thumbnail_url: Optional[str], settings: Settings) -> str:
    if thumbnail_url and "image.mux.com" in thumbnail_url:
        sep = "&" if "?" in thumbnail_url else "?"
        return f"{thumbnail_url}{sep}width=1200&height=630&fit_mode=smartcrop"
    if thumbnail_url:
        return thumbnail_url
    return f"{settings.share_web_base_url}/share-static/og-default.png"


def build_share_context(
    message: dict, masjid: dict, settings: Settings
) -> dict:
    message_id = str(message.get("id") or message.get("_id") or "")
    name = (masjid.get("name") or "").strip() or "This masjid"
    location = ", ".join(
        p for p in [masjid.get("city"), masjid.get("state")] if p and str(p).strip()
    ) or (masjid.get("address") or "")
    verified = bool((masjid.get("management") or {}).get("is_claimed"))

    text = (message.get("text") or "").strip()
    og_description = (
        (text[: _OG_DESC_MAX - 1] + "…") if len(text) > _OG_DESC_MAX else text
    ) or f"New announcement from {name}"

    msg_type = message.get("message_type") or "text"
    video_url = message.get("video_url") or None
    thumbnail_url = message.get("thumbnail_url") or None
    is_video = msg_type == "video" and bool(video_url)

    return {
        "message_id": message_id,
        "masjid_name": name,
        "masjid_location": location,
        "masjid_verified": verified,
        "masjid_avatar_url": masjid.get("photo_url")
        or f"{settings.share_web_base_url}/share-static/masjid-default.png",
        "is_video": is_video,
        "video_hls_url": video_url,
        "poster_url": thumbnail_url,
        "og_image_url": _sized_og_image(thumbnail_url, settings),
        "og_description": og_description,
        "page_title": f"{name} — announcement | Muslim 360",
        "relative_time": _relative_time(message.get("created_at")),
        "canonical_url": f"{settings.share_web_base_url}/s/{message_id}",
        "deep_link_path": f"/s/{message_id}",
        "share_host": settings.share_host,
        "play_store_url": settings.play_store_url,
        "app_store_url": settings.app_store_url,
        "android_package": settings.android_package_name,
        "marketing_site_url": settings.marketing_site_url,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_share_context.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/web/share_context.py tests/test_share_context.py
git commit -m "feat(share): SharePageContext builder

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AEubAUb6psgKtPEMaDW13Z"
```

---

### Task 3: Extend the public broadcast payload

**Files:**
- Modify: `app/api/v1/endpoints/broadcast.py:28-44` (`get_public_broadcast`)
- Test: `tests/test_broadcast_public_endpoint.py`

**Interfaces:**
- Consumes: `build_share_context` not used here; this only reshapes the JSON API response.
- Produces: `GET /api/v1/broadcast/public/{message_id}` response `data.masjid` now also has
  `id`, `place_id`, `state`, `verified` (bool), `photo_url`; `data.message` unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broadcast_public_endpoint.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_broadcast_public_endpoint.py -v`
Expected: FAIL — `KeyError: 'id'` / assertion error (extras missing)

- [ ] **Step 3: Update `get_public_broadcast` in `app/api/v1/endpoints/broadcast.py`**

Replace the `return success_response({...})` block (lines 37-44) with:

```python
    return success_response({
        "message": msg,
        "masjid": {
            "id": masjid_data.get("id", ""),
            "place_id": masjid_data.get("place_id", ""),
            "name": masjid_data.get("name", ""),
            "city": masjid_data.get("city", ""),
            "state": masjid_data.get("state", ""),
            "address": masjid_data.get("address", ""),
            "photo_url": masjid_data.get("photo_url", ""),
            "verified": bool((masjid_data.get("management") or {}).get("is_claimed")),
        },
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_broadcast_public_endpoint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/endpoints/broadcast.py tests/test_broadcast_public_endpoint.py
git commit -m "feat(share): add masjid id/place_id/state/verified/photo to public broadcast

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AEubAUb6psgKtPEMaDW13Z"
```

---

### Task 4: Share page route `/s/{message_id}` + `share.html`

**Files:**
- Modify: `app/web/share.py` (add the `/s/{message_id}` route + a Jinja2 `Environment`)
- Create: `app/web/templates/share.html`
- Create: `app/web/static/og-default.png` (1200×630 solid brand-green PNG with the M360 logo — generate with the snippet in Step 3)
- Create: `app/web/static/masjid-default.png` (256×256 neutral mosque glyph — reuse `app/web/static/logo.png` copied to this name is acceptable)
- Test: extend `tests/test_share_wellknown.py` → rename mentally to cover `/s/` too (keep file name)

**Interfaces:**
- Consumes: `build_share_context` (Task 2), `get_broadcast_feed_service`, `get_masjid_entity_service`, `ApiException` (has `.status_code`).
- Produces: `GET /s/{message_id}` → `HTMLResponse` (200 with `Cache-Control: public, max-age=300`) or 404 HTML page.

- [ ] **Step 1: Write the failing test (append to `tests/test_share_wellknown.py`)**

```python
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
    assert "image.mux.com/a/thumbnail.jpg?width=1200&height=630" in html
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_share_wellknown.py -v -k share_page`
Expected: FAIL — 404 route not found / 500

- [ ] **Step 3: Generate the static images**

```bash
cd m360-backend
.venv/bin/python - <<'PY'
from PIL import Image, ImageDraw
img = Image.new("RGB", (1200, 630), (69, 208, 124))
d = ImageDraw.Draw(img)
d.text((60, 60), "Muslim 360", fill=(9, 25, 20))
img.save("app/web/static/og-default.png")
PY
cp app/web/static/logo.png app/web/static/masjid-default.png
```

If Pillow is not installed, `cp app/web/static/logo.png app/web/static/og-default.png` is an acceptable fallback — the OG default only shows when a broadcast has no Mux thumbnail.

- [ ] **Step 4: Add the `/s/{message_id}` route to `app/web/share.py`**

Add near the top (module level):

```python
from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api.deps import get_broadcast_feed_service, get_masjid_entity_service
from app.exceptions.base import ApiException
from app.web.share_context import build_share_context

_env = Environment(
    loader=FileSystemLoader("app/web/templates"),
    autoescape=select_autoescape(["html"]),
)
```

Add the route:

```python
@router.get("/s/{message_id}", response_class=HTMLResponse)
def share_page(
    message_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    feed_svc=Depends(get_broadcast_feed_service),
    masjid_svc=Depends(get_masjid_entity_service),
) -> HTMLResponse:
    try:
        message = feed_svc.get_message_raw(message_id)
        masjid_wrap = masjid_svc.get_masjid(message["masjid_id"])
        masjid = (masjid_wrap or {}).get("masjid", {}) if masjid_wrap else {}
    except ApiException as exc:
        if getattr(exc, "status_code", 500) == 404:
            html = _env.get_template("share_not_found.html").render(
                marketing_site_url=settings.marketing_site_url
            )
            return HTMLResponse(html, status_code=404)
        raise

    ctx = build_share_context(message, masjid, settings)
    html = _env.get_template("share.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
```

- [ ] **Step 5: Create `app/web/templates/share_not_found.html`**

```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Announcement not available | Muslim 360</title>
<style>
  body{margin:0;font-family:-apple-system,"Plus Jakarta Sans",system-ui,sans-serif;
    background:#F8F9FA;color:#091914;display:flex;min-height:100vh;
    align-items:center;justify-content:center;text-align:center;padding:24px}
  a{display:inline-block;margin-top:16px;background:linear-gradient(#61D47D,#ADFF8D);
    color:#091914;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:12px}
</style></head><body><div>
  <h1>This announcement is no longer available</h1>
  <p>It may have been removed by the masjid.</p>
  <a href="{{ marketing_site_url }}">Open Muslim 360</a>
</div></body></html>
```

- [ ] **Step 6: Create `app/web/templates/share.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{ page_title }}</title>
<meta name="description" content="{{ og_description }}">

<meta property="og:site_name" content="Muslim 360">
<meta property="og:title" content="{{ masjid_name }}">
<meta property="og:description" content="{{ og_description }}">
<meta property="og:type" content="video.other">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:image" content="{{ og_image_url }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
{% if video_hls_url %}
<meta property="og:video" content="{{ video_hls_url }}">
<meta property="og:video:type" content="application/x-mpegURL">
{% endif %}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ masjid_name }}">
<meta name="twitter:description" content="{{ og_description }}">
<meta name="twitter:image" content="{{ og_image_url }}">

<style>
  :root{--green:#45D07C;--ink:#091914;--muted:#5D6C67;--line:#EDEFF1;--bg:#F2F3F5}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,"Plus Jakarta Sans",system-ui,Segoe UI,Roboto,sans-serif}
  .wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#fff;
    display:flex;flex-direction:column}
  .topbar{display:flex;align-items:center;justify-content:space-between;
    padding:12px 16px;border-bottom:1px solid var(--line)}
  .brand{display:flex;align-items:center;gap:10px}
  .brand img{width:36px;height:36px;border-radius:9px}
  .brand small{display:block;color:var(--muted);font-size:11px;line-height:1.1}
  .brand strong{font-size:15px}
  .close{border:0;background:transparent;font-size:22px;color:var(--ink);
    cursor:pointer;line-height:1;text-decoration:none}
  .media{position:relative;flex:1;min-height:60vh;background:#000;
    display:flex;align-items:center;justify-content:center;overflow:hidden}
  .media video,.media img.poster{width:100%;height:100%;object-fit:cover}
  .playbtn{position:absolute;width:72px;height:72px;border-radius:50%;
    background:rgba(255,255,255,.35);backdrop-filter:blur(6px);border:0;cursor:pointer;
    display:flex;align-items:center;justify-content:center}
  .playbtn::after{content:"";border-style:solid;border-width:14px 0 14px 22px;
    border-color:transparent transparent transparent #091914;margin-left:5px}
  .card{padding:16px}
  .row{display:flex;align-items:center;gap:12px}
  .avatar{width:48px;height:48px;border-radius:50%;object-fit:cover;flex:0 0 48px}
  .name{font-weight:700;font-size:18px;display:flex;align-items:center;gap:6px}
  .check{width:16px;height:16px;fill:#2D9CDB;flex:0 0 16px}
  .loc{color:var(--muted);font-size:13px}
  .time{margin-left:auto;color:var(--muted);font-size:12px;white-space:nowrap}
  .text{margin:14px 2px 0;font-size:14px;line-height:1.5}
  .btns{display:flex;gap:10px;padding:16px}
  .btns button{flex:1;padding:13px 0;border-radius:12px;font-size:14px;font-weight:600;
    cursor:pointer;font-family:inherit}
  .primary{border:0;background:linear-gradient(#61D47D,#ADFF8D);color:#091914}
  .ghost{border:1px solid var(--green);background:#fff;color:#0B7C43}
  .toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);
    background:#091914;color:#fff;padding:10px 16px;border-radius:20px;font-size:13px;
    opacity:0;transition:opacity .2s;pointer-events:none}
  .toast.show{opacity:1}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div class="brand">
      <img src="/share-static/logo.png" alt="Muslim 360">
      <span><small>Powered by</small><strong>Muslim 360</strong></span>
    </div>
    <a class="close" href="{{ marketing_site_url }}" aria-label="Close">&times;</a>
  </div>

  <div class="media" id="media">
    {% if is_video %}
      <img class="poster" src="{{ poster_url or og_image_url }}" alt="">
      <button class="playbtn" id="play" aria-label="Play"></button>
      <video id="v" playsinline preload="none" poster="{{ poster_url or '' }}" hidden></video>
    {% else %}
      <img class="poster" src="{{ poster_url or og_image_url }}" alt="">
    {% endif %}
  </div>

  <div class="card">
    <div class="row">
      <img class="avatar" src="{{ masjid_avatar_url }}" alt="">
      <div>
        <div class="name">{{ masjid_name }}
          {% if masjid_verified %}
          <svg class="check" viewBox="0 0 24 24"><path d="M12 2l2.4 2.1 3.1-.5.9 3 2.9 1.3-1.3 2.9 1.3 2.9-2.9 1.3-.9 3-3.1-.5L12 22l-2.4-2.1-3.1.5-.9-3-2.9-1.3 1.3-2.9L1.7 8l2.9-1.3.9-3 3.1.5z"/><path d="M10.6 14.6l-2.2-2.2-1.4 1.4 3.6 3.6 6-6-1.4-1.4z" fill="#fff"/></svg>
          {% endif %}
        </div>
        <div class="loc">{{ masjid_location }}</div>
      </div>
      <div class="time">{{ relative_time }}</div>
    </div>
    {% if og_description %}<p class="text">{{ og_description }}</p>{% endif %}
  </div>

  <div class="btns">
    <button class="primary" onclick="openApp()">Follow Masjid</button>
    <button class="ghost" onclick="sharePage()">Share</button>
  </div>
</div>
<div class="toast" id="toast">Link copied</div>

<script>
  var SHARE_HOST = {{ share_host | tojson }};
  var DEEP_PATH = {{ deep_link_path | tojson }};
  var PLAY_URL = {{ play_store_url | tojson }};
  var APPSTORE_URL = {{ app_store_url | tojson }};
  var ANDROID_PKG = {{ android_package | tojson }};
  var HLS_URL = {{ (video_hls_url or "") | tojson }};

  function openApp() {
    var ua = navigator.userAgent || "";
    var isAndroid = /android/i.test(ua);
    var isIOS = /iphone|ipad|ipod/i.test(ua);
    var store = isIOS ? APPSTORE_URL : PLAY_URL;
    var start = Date.now();
    setTimeout(function () {
      if (Date.now() - start < 2000 && !document.hidden) window.location = store;
    }, 1100);
    if (isAndroid) {
      window.location =
        "intent://" + SHARE_HOST + DEEP_PATH +
        "#Intent;scheme=https;package=" + ANDROID_PKG +
        ";S.browser_fallback_url=" + encodeURIComponent(store) + ";end";
    } else {
      window.location = "https://" + SHARE_HOST + DEEP_PATH;
    }
  }

  function sharePage() {
    var url = window.location.href;
    if (navigator.share) {
      navigator.share({ title: document.title, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(function () {
        var t = document.getElementById("toast");
        t.classList.add("show");
        setTimeout(function () { t.classList.remove("show"); }, 1600);
      });
    }
  }

  var playBtn = document.getElementById("play");
  if (playBtn) {
    playBtn.addEventListener("click", function () {
      var v = document.getElementById("v");
      var poster = document.querySelector(".media .poster");
      playBtn.hidden = true;
      if (poster) poster.hidden = true;
      v.hidden = false;
      v.controls = true;
      function go() { v.play().catch(function () {}); }
      if (v.canPlayType("application/vnd.apple.mpegurl")) {
        v.src = HLS_URL; go();
      } else {
        var s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js";
        s.onload = function () {
          if (window.Hls && window.Hls.isSupported()) {
            var hls = new window.Hls();
            hls.loadSource(HLS_URL);
            hls.attachMedia(v);
            hls.on(window.Hls.Events.MANIFEST_PARSED, go);
          } else { v.src = HLS_URL; go(); }
        };
        document.head.appendChild(s);
      }
    });
  }
</script>
</body>
</html>
```

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_share_wellknown.py tests/test_share_context.py -v`
Expected: PASS (all)

- [ ] **Step 8: Manual eyeball**

Run: `.venv/bin/uvicorn main:app --port 8002` then in another shell
`curl -s localhost:8002/s/anything | head -40` (will 404-render without a DB — that is fine;
confirm it returns the not-found HTML, not a stack trace).

- [ ] **Step 9: Commit**

```bash
git add app/web/share.py app/web/templates/share.html app/web/templates/share_not_found.html app/web/static/og-default.png app/web/static/masjid-default.png tests/test_share_wellknown.py
git commit -m "feat(share): server-rendered /s/{id} share page with OG metadata

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AEubAUb6psgKtPEMaDW13Z"
```

---

### Task 5: `.env` documentation + README note

**Files:**
- Modify: `m360-backend/.env` (append the new keys, commented, with placeholder values)
- Modify: `m360-backend/README.md` (add a short "Share page / deep links" subsection near the env docs ~line 175)

**Interfaces:** none (docs only).

- [ ] **Step 1: Append to `.env`**

```
# --- Share page / deep linking ---
SHARE_WEB_BASE_URL=https://share.vyapari.link
# Comma-separated SHA-256 fingerprints of the Android release signing cert(s)
ANDROID_SHA256_CERT_FINGERPRINTS=
# Apple Developer Team ID (10 chars) — required for iOS Universal Links
APPLE_TEAM_ID=
```

- [ ] **Step 2: Add README subsection**

```markdown
### Share page / deep links

The backend serves `GET /s/{broadcastMessageId}` (branded share page with Open Graph
metadata) plus `/.well-known/assetlinks.json` and `/.well-known/apple-app-site-association`
for Android App Links / iOS Universal Links. Configure via `SHARE_WEB_BASE_URL`,
`ANDROID_SHA256_CERT_FINGERPRINTS`, `APPLE_TEAM_ID` (see `.env`). The host in
`SHARE_WEB_BASE_URL` must serve this app over HTTPS and match the Flutter app's
intent-filter / associated-domain.
```

- [ ] **Step 3: Commit**

```bash
git add .env README.md
git commit -m "docs(share): document share/deeplink env vars

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AEubAUb6psgKtPEMaDW13Z"
```

> **Backend phase gate:** run `.venv/bin/pytest -q` — full suite green before moving to Phase 2.

---

## Phase 2 — Flutter app (`m360-flutter-app`)

> All commands below run from `m360-flutter-app/`. Commit messages carry the same
> `Co-Authored-By` / `Claude-Session` trailers.

### Task 6: `app_links` dependency + `SHARE_BASE_URL` env

**Files:**
- Modify: `pubspec.yaml` (add `app_links: ^6.3.0` under `dependencies`, alphabetically near `adhan_dart`)
- Modify: `.env.dev` (append `SHARE_BASE_URL=https://share.vyapari.link`)
- Modify: `m360-flutter-app/CLAUDE.md` — add `app_links` + `SHARE_BASE_URL` to the env/deps tables

**Interfaces:**
- Produces: `dotenv.env['SHARE_BASE_URL']` available at runtime; `package:app_links/app_links.dart` importable.

- [ ] **Step 1: Add the dependency**

Edit `pubspec.yaml` — add `  app_links: ^6.3.0` in the `dependencies:` block.

- [ ] **Step 2: Fetch**

Run: `flutter pub get`
Expected: resolves, `app_links` + platform plugins registered.

- [ ] **Step 3: Append to `.env.dev`**

```
SHARE_BASE_URL=https://share.vyapari.link
```

- [ ] **Step 4: Update `CLAUDE.md`** — add row `| SHARE_BASE_URL | Base URL of the web share page (deep links) |` to the env keys list and `| app_links | Incoming deep link handling |` to the packages table.

- [ ] **Step 5: Commit**

```bash
git add pubspec.yaml pubspec.lock .env.dev CLAUDE.md
git commit -m "chore(deeplink): add app_links dep + SHARE_BASE_URL env"
```

---

### Task 7: `parseShareLink` pure function

**Files:**
- Create: `lib/services/deep_link_parser.dart`
- Test: `test/deep_link_parser_test.dart`

**Interfaces:**
- Produces: `String? parseShareMessageId(Uri uri, {required String shareHost})` — returns the
  message id when `uri.host == shareHost` (case-insensitive) and path matches `/s/<id>`
  with `id` in `^[A-Za-z0-9_-]+$`; otherwise `null`.

- [ ] **Step 1: Write the failing test**

```dart
// test/deep_link_parser_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/deep_link_parser.dart';

void main() {
  const host = 'share.vyapari.link';
  String? p(String u) => parseShareMessageId(Uri.parse(u), shareHost: host);

  test('valid link', () {
    expect(p('https://share.vyapari.link/s/652f0abc'), '652f0abc');
  });
  test('trailing slash ok', () {
    expect(p('https://share.vyapari.link/s/652f0abc/'), '652f0abc');
  });
  test('case-insensitive host', () {
    expect(p('https://Share.Vyapari.Link/s/abc-1_2'), 'abc-1_2');
  });
  test('wrong host -> null', () {
    expect(p('https://evil.com/s/652f0abc'), isNull);
  });
  test('wrong path -> null', () {
    expect(p('https://share.vyapari.link/x/652f0abc'), isNull);
    expect(p('https://share.vyapari.link/s/'), isNull);
    expect(p('https://share.vyapari.link/s/a/b'), isNull);
  });
  test('bad chars -> null', () {
    expect(p('https://share.vyapari.link/s/a b'), isNull);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/deep_link_parser_test.dart`
Expected: FAIL — target of URI doesn't exist (`deep_link_parser.dart`)

- [ ] **Step 3: Create `lib/services/deep_link_parser.dart`**

```dart
final _idPattern = RegExp(r'^[A-Za-z0-9_-]+$');

/// Extracts the broadcast message id from an incoming share link, or null when
/// the URI is not one of ours.
String? parseShareMessageId(Uri uri, {required String shareHost}) {
  if (uri.host.toLowerCase() != shareHost.toLowerCase()) return null;
  final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
  if (segments.length != 2 || segments[0] != 's') return null;
  final id = segments[1];
  if (!_idPattern.hasMatch(id)) return null;
  return id;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/deep_link_parser_test.dart`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/services/deep_link_parser.dart test/deep_link_parser_test.dart
git commit -m "feat(deeplink): parseShareMessageId pure function"
```

---

### Task 8: `BroadcastService.getPublicBroadcast`

**Files:**
- Modify: `lib/services/api_services/broadcast_service.dart` (add model + method)
- Test: `test/public_broadcast_test.dart`

**Interfaces:**
- Consumes: `ApiService` (Dio wrapper), `dotenv.env['API_BASE_URL']`.
- Produces:
  - `class PublicBroadcast { final String messageId, masjidId, masjidName, masjidPlaceId, masjidPhotoUrl; final bool masjidVerified; PublicBroadcast.fromApi(Map<String,dynamic> data); }`
  - `Future<PublicBroadcast> BroadcastService.getPublicBroadcast(String messageId)` — hits
    `GET {API_BASE_URL}/broadcast/public/{messageId}` **without** an auth header, parses
    `response.data['data']`.

- [ ] **Step 1: Write the failing test**

```dart
// test/public_broadcast_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/api_services/broadcast_service.dart';

void main() {
  test('PublicBroadcast.fromApi maps message + masjid', () {
    final data = {
      'message': {'id': 'm1', 'masjid_id': 'mid1', 'text': 'hi'},
      'masjid': {
        'id': 'mid1', 'place_id': 'ChIJ1', 'name': 'Masjid Al Noor',
        'photo_url': 'https://cdn/x.jpg', 'verified': true,
      },
    };
    final pb = PublicBroadcast.fromApi(data);
    expect(pb.messageId, 'm1');
    expect(pb.masjidId, 'mid1');
    expect(pb.masjidPlaceId, 'ChIJ1');
    expect(pb.masjidName, 'Masjid Al Noor');
    expect(pb.masjidPhotoUrl, 'https://cdn/x.jpg');
    expect(pb.masjidVerified, true);
  });

  test('fromApi tolerates missing masjid fields', () {
    final pb = PublicBroadcast.fromApi({
      'message': {'id': 'm2', 'masjid_id': 'mid2'},
      'masjid': {},
    });
    expect(pb.messageId, 'm2');
    expect(pb.masjidId, 'mid2');
    expect(pb.masjidName, '');
    expect(pb.masjidVerified, false);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/public_broadcast_test.dart`
Expected: FAIL — `PublicBroadcast` undefined

- [ ] **Step 3: Add to `broadcast_service.dart`**

Add the model above `class BroadcastService`:

```dart
class PublicBroadcast {
  final String messageId;
  final String masjidId;
  final String masjidName;
  final String masjidPlaceId;
  final String masjidPhotoUrl;
  final bool masjidVerified;

  PublicBroadcast({
    required this.messageId,
    required this.masjidId,
    required this.masjidName,
    required this.masjidPlaceId,
    required this.masjidPhotoUrl,
    required this.masjidVerified,
  });

  factory PublicBroadcast.fromApi(Map<String, dynamic> data) {
    final msg = (data['message'] as Map<String, dynamic>?) ?? const {};
    final masjid = (data['masjid'] as Map<String, dynamic>?) ?? const {};
    return PublicBroadcast(
      messageId: (msg['id'] ?? msg['_id'] ?? '') as String,
      masjidId: (msg['masjid_id'] ?? masjid['id'] ?? '') as String,
      masjidName: (masjid['name'] ?? '') as String,
      masjidPlaceId: (masjid['place_id'] ?? '') as String,
      masjidPhotoUrl: (masjid['photo_url'] ?? '') as String,
      masjidVerified: (masjid['verified'] ?? false) as bool,
    );
  }
}
```

Add the method inside `class BroadcastService`:

```dart
  Future<PublicBroadcast> getPublicBroadcast(String messageId) async {
    final apiService = ApiService(baseUrl: baseUrl);
    final response = await apiService.get('/broadcast/public/$messageId');
    final data = response.data as Map<String, dynamic>;
    return PublicBroadcast.fromApi(
      data['data'] as Map<String, dynamic>? ?? const {},
    );
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/public_broadcast_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/services/api_services/broadcast_service.dart test/public_broadcast_test.dart
git commit -m "feat(deeplink): BroadcastService.getPublicBroadcast"
```

---

### Task 9: `BottomNav` initial-tab support

**Files:**
- Modify: `lib/features/home/bottom_nav.dart:10-19` (constructor + `_currentIndex` init)
- Modify: `lib/app/routes.dart:21-25` (`case bottomNav:` — read `args['tab']`)
- Test: `test/bottom_nav_initial_index_test.dart`

**Interfaces:**
- Consumes: nothing new.
- Produces: `BottomNav({Key? key, int initialIndex = 0})`; `routes.dart` maps
  `arguments = {'tab': 'masjid'}` → `initialIndex: 2` (tab order: 0 home, 1 quran,
  2 masjid, 3 settings).

- [ ] **Step 1: Write the failing test**

```dart
// test/bottom_nav_initial_index_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/app/routes.dart';

void main() {
  test('bottomNav route maps tab arg to masjid index', () {
    final route = AppRoutes.generateRoute(
      const RouteSettings(name: AppRoutes.bottomNav, arguments: {'tab': 'masjid'}),
    ) as MaterialPageRoute;
    // BottomNav is const with initialIndex; build it and read the field via the
    // widget it returns.
    final ctx = _FakeContext();
    final widget = route.builder(ctx);
    expect(widget.toString(), contains('BottomNav'));
  });
}

class _FakeContext extends StatelessElement {
  _FakeContext() : super(_D());
}
class _D extends StatelessWidget {
  @override
  Widget build(BuildContext context) => const SizedBox();
}
```

> Note: if wiring a fake `BuildContext` proves awkward, replace this test with a
> `testWidgets` that pumps `MaterialApp(onGenerateRoute: AppRoutes.generateRoute,
> initialRoute: AppRoutes.bottomNav)` with `onGenerateInitialRoutes` supplying
> `{'tab':'masjid'}`, then `expect(find.byType(MasjidScreen), findsOneWidget)` after
> `tester.pumpAndSettle()`. Prefer whichever compiles cleanly first.

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/bottom_nav_initial_index_test.dart`
Expected: FAIL — `initialIndex` not a param / arg ignored

- [ ] **Step 3: Edit `bottom_nav.dart`**

```dart
class BottomNav extends StatefulWidget {
  const BottomNav({super.key, this.initialIndex = 0});
  final int initialIndex;

  @override
  State<BottomNav> createState() => _BottomNavState();
}

class _BottomNavState extends State<BottomNav> {
  late int _currentIndex = widget.initialIndex;
  // ...rest unchanged
```

- [ ] **Step 4: Edit `routes.dart` `case bottomNav:`**

```dart
      case bottomNav:
        final navArgs = settings.arguments;
        int initialIndex = 0;
        if (navArgs is Map && navArgs['tab'] == 'masjid') initialIndex = 2;
        return MaterialPageRoute(
          builder: (_) => BottomNav(initialIndex: initialIndex),
          settings: settings,
        );
```

Add `import '../features/home/bottom_nav.dart';` if not already present (it is — line 6).

- [ ] **Step 5: Run test to verify it passes**

Run: `flutter test test/bottom_nav_initial_index_test.dart`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add lib/features/home/bottom_nav.dart lib/app/routes.dart test/bottom_nav_initial_index_test.dart
git commit -m "feat(deeplink): BottomNav initialIndex + route arg for masjid tab"
```

---

### Task 10: `DeepLinkService` — resolve + navigate

**Files:**
- Create: `lib/services/deep_link_service.dart`
- Modify: `lib/l10n/app_en.arb` + `lib/l10n/app_hi.arb` (one key: `deeplink_unavailable`)
- Test: `test/deep_link_service_test.dart`

**Interfaces:**
- Consumes: `parseShareMessageId` (Task 7), `BroadcastService.getPublicBroadcast` +
  `PublicBroadcast` (Task 8), `MasjidEntityService.instance.getMasjid` (returns
  `MasjidEntity` with `.currentUserRelationship`, `.followerCount`, `.photoUrl`,
  `.management`), `Masjid.fromJson` (`masjid_service.dart`), `NavigationService.navigatorKey`,
  `StoreManager.instance.accessToken`, `AppRoutes`.
- Produces:
  - `class DeepLinkService` singleton `DeepLinkService.instance`
  - `Future<void> init()` — idempotent; subscribes to `AppLinks().uriLinkStream`, consumes
    `getInitialLink()`, queues until `markReady()` is called.
  - `void markReady()` — called once the first frame + store bootstrap are done; flushes a
    queued link.
  - `Future<void> handleUri(Uri uri)` — visible for tests; parse → resolve → navigate.
  - `NavPlan planNavigation(PublicBroadcast pb, MasjidEntity masjid, {required bool loggedIn})`
    — **pure**, returns `NavPlan(needsLogin: bool, openFeed: bool)` where
    `openFeed == masjidIsFollowed(masjid) && announcementsEnabled(masjid)`.

- [ ] **Step 1: Write the failing test (pure decision logic only)**

```dart
// test/deep_link_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/api_services/broadcast_service.dart';
import 'package:m360/services/api_services/masjid_entity_service.dart';
import 'package:m360/services/deep_link_service.dart';

PublicBroadcast _pb() => PublicBroadcast(
      messageId: 'm1', masjidId: 'mid1', masjidName: 'Al Noor',
      masjidPlaceId: 'ChIJ1', masjidPhotoUrl: '', masjidVerified: true,
    );

MasjidEntity _masjid({String? rel, bool announcements = true}) => MasjidEntity(
      id: 'mid1', name: 'Al Noor', address: '', city: 'Moradabad',
      latitude: 0, longitude: 0, followerCount: 3,
      currentUserRelationship: rel,
      services: announcements ? {'announcements_enabled': true} : {},
    );

void main() {
  final svc = DeepLinkService.instance;

  test('logged out -> needs login', () {
    final plan = svc.planNavigation(_pb(), _masjid(rel: 'follower'), loggedIn: false);
    expect(plan.needsLogin, true);
  });

  test('followed + announcements -> open feed', () {
    final plan = svc.planNavigation(_pb(), _masjid(rel: 'follower'), loggedIn: true);
    expect(plan.needsLogin, false);
    expect(plan.openFeed, true);
  });

  test('not followed -> stop at detail', () {
    final plan = svc.planNavigation(_pb(), _masjid(rel: null), loggedIn: true);
    expect(plan.openFeed, false);
  });

  test('followed but announcements disabled -> stop at detail', () {
    final plan = svc.planNavigation(
      _pb(), _masjid(rel: 'follower', announcements: false), loggedIn: true);
    expect(plan.openFeed, false);
  });
}
```

> Adjust `_masjid(...)` field names to the real `MasjidEntity` constructor if they differ
> (check `lib/services/api_services/masjid_entity_service.dart`); the constructor there
> takes named params `id/name/address/city/latitude/longitude` as required and the rest
> optional. `announcementsEnabled` reads `masjid.services?['announcements_enabled'] == true`
> OR `masjid.management?['announcements_enabled'] == true` — use whichever the API actually
> populates (grep `announcements_enabled` / `hasAnnouncementsEnabled` in the repo; fall
> back to `true` if the entity carries no such flag, so the feed still opens for followers).

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/deep_link_service_test.dart`
Expected: FAIL — `DeepLinkService` / `NavPlan` undefined

- [ ] **Step 3: Add ARB key**

`app_en.arb`: `"deeplink_unavailable": "This announcement is no longer available",`
`app_hi.arb`: `"deeplink_unavailable": "यह घोषणा अब उपलब्ध नहीं है",`
Run: `flutter gen-l10n`

- [ ] **Step 4: Create `lib/services/deep_link_service.dart`**

```dart
import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'package:m360/app/navigation_service.dart';
import 'package:m360/app/routes.dart';
import 'package:m360/features/home/screens/broadcast/broadcast_feed.dart';
import 'package:m360/features/home/screens/masjid/masjid_details.dart';
import 'package:m360/l10n/app_localizations.dart';
import 'package:m360/services/api_services/broadcast_service.dart';
import 'package:m360/services/api_services/masjid_entity_service.dart';
import 'package:m360/services/api_services/masjid_service.dart';
import 'package:m360/services/deep_link_parser.dart';
import 'package:m360/services/store_manager.dart';

class NavPlan {
  final bool needsLogin;
  final bool openFeed;
  const NavPlan({required this.needsLogin, required this.openFeed});
}

class DeepLinkService {
  DeepLinkService._();
  static final DeepLinkService instance = DeepLinkService._();

  final AppLinks _appLinks = AppLinks();
  StreamSubscription<Uri>? _sub;
  bool _initialized = false;
  bool _ready = false;
  Uri? _pending;

  String get _shareHost {
    final raw = dotenv.env['SHARE_BASE_URL'] ?? 'https://share.vyapari.link';
    return Uri.parse(raw).host;
  }

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;
    _sub = _appLinks.uriLinkStream.listen(_onUri, onError: (_) {});
    try {
      final initial = await _appLinks.getInitialLink();
      if (initial != null) _onUri(initial);
    } catch (_) {}
  }

  void markReady() {
    _ready = true;
    final p = _pending;
    if (p != null) {
      _pending = null;
      handleUri(p);
    }
  }

  void _onUri(Uri uri) {
    if (!_ready) {
      _pending = uri;
      return;
    }
    handleUri(uri);
  }

  @visibleForTesting
  Future<void> handleUri(Uri uri) async {
    final id = parseShareMessageId(uri, shareHost: _shareHost);
    if (id == null) return;
    final nav = NavigationService.navigatorKey.currentState;
    if (nav == null) {
      _pending = uri;
      return;
    }
    try {
      final pb = await BroadcastService.instance.getPublicBroadcast(id);
      final masjid = await MasjidEntityService.instance.getMasjid(pb.masjidId);
      final loggedIn = StoreManager.instance.accessToken != null;
      final plan = planNavigation(pb, masjid, loggedIn: loggedIn);

      if (plan.needsLogin) {
        nav.pushNamed(AppRoutes.login, arguments: {
          'return_route': AppRoutes.bottomNav,
          'pop_on_success': false,
        });
        // After login the user lands on home; re-fire the link so it resolves
        // fully now that a token exists.
        _pending = uri;
        return;
      }

      await nav.pushNamedAndRemoveUntil(
        AppRoutes.bottomNav,
        (r) => false,
        arguments: const {'tab': 'masjid'},
      );
      final masjidModel = Masjid.fromJson(masjid.toJson());
      nav.push(MaterialPageRoute(
        builder: (_) => MasjidDetailsScreen(masjid: masjidModel, hasDetails: true),
      ));
      if (plan.openFeed) {
        nav.push(MaterialPageRoute(
          builder: (_) => BroadcastFeedScreen(
            masjidId: pb.masjidId,
            masjidName: pb.masjidName,
            followerCount: masjid.followerCount ?? 0,
            masjidPhotoUrl: pb.masjidPhotoUrl.isEmpty ? null : pb.masjidPhotoUrl,
          ),
        ));
      }
    } catch (_) {
      final ctx = NavigationService.navigatorKey.currentContext;
      if (ctx != null) {
        final l10n = AppLocalizations.of(ctx);
        ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
          content: Text(l10n?.deeplink_unavailable ??
              'This announcement is no longer available'),
        ));
      }
    }
  }

  NavPlan planNavigation(
    PublicBroadcast pb,
    MasjidEntity masjid, {
    required bool loggedIn,
  }) {
    if (!loggedIn) return const NavPlan(needsLogin: true, openFeed: false);
    final rel = (masjid.currentUserRelationship ?? '').toLowerCase();
    final followed = rel.contains('follow') || rel.contains('member') ||
        rel == 'saved';
    final announcementsEnabled =
        (masjid.services?['announcements_enabled'] == true) ||
        (masjid.management?['announcements_enabled'] == true) ||
        masjid.services == null; // no flag from API -> don't block followers
    return NavPlan(
      needsLogin: false,
      openFeed: followed && announcementsEnabled,
    );
  }

  void dispose() {
    _sub?.cancel();
  }
}
```

> During implementation, verify `MasjidEntity` exposes `toJson()` (it does — grep confirms
> a `toJson` near line 74). If `Masjid.fromJson` chokes on the entity JSON shape, build the
> `Masjid` explicitly from `masjid.placeId/name/address` + a `Location` — keep it minimal;
> `MasjidDetailsScreen` re-fetches full details from the id.

- [ ] **Step 5: Run test to verify it passes**

Run: `flutter test test/deep_link_service_test.dart test/deep_link_parser_test.dart`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add lib/services/deep_link_service.dart lib/l10n/ test/deep_link_service_test.dart
git commit -m "feat(deeplink): DeepLinkService resolves /s/{id} to masjid + builds stack"
```

---

### Task 11: Wire `DeepLinkService` into `main.dart`

**Files:**
- Modify: `lib/main.dart` (import + `init()` before `runApp`, `markReady()` in the
  post-first-frame callback)

**Interfaces:**
- Consumes: `DeepLinkService.instance` (Task 10).

- [ ] **Step 1: Edit `lib/main.dart`**

Add import: `import 'package:m360/services/deep_link_service.dart';`

After `await AnalyticsService.instance.initializeUserId();` (before `runApp`):

```dart
  await DeepLinkService.instance.init();
```

Inside the existing `WidgetsBinding.instance.addPostFrameCallback((_) async { ... })` block,
as the first line:

```dart
    DeepLinkService.instance.markReady();
```

- [ ] **Step 2: Static check**

Run: `flutter analyze lib/main.dart lib/services/deep_link_service.dart`
Expected: no errors (warnings about `print` in main are pre-existing, ignore).

- [ ] **Step 3: Build smoke test**

Run: `flutter build apk --debug --dart-define=ENV=.env.dev`
Expected: BUILD SUCCESSFUL

- [ ] **Step 4: Commit**

```bash
git add lib/main.dart
git commit -m "feat(deeplink): initialise DeepLinkService on startup"
```

---

### Task 12: Android App Links intent-filter

**Files:**
- Modify: `android/app/src/main/AndroidManifest.xml` (add an intent-filter to `.MainActivity`)

**Interfaces:** none (native config).

- [ ] **Step 1: Locate the `.MainActivity` `<activity>` block**

It currently holds the `MAIN` / `LAUNCHER` intent-filter (around line 60).

- [ ] **Step 2: Add a second intent-filter inside the same `<activity>`**

```xml
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data
                    android:scheme="https"
                    android:host="share.vyapari.link"
                    android:pathPrefix="/s" />
            </intent-filter>
```

- [ ] **Step 3: Build**

Run: `flutter build apk --debug --dart-define=ENV=.env.dev`
Expected: BUILD SUCCESSFUL

- [ ] **Step 4: Manual device check (documented, not automated)**

With a debug build installed and the backend deployed at the real host:
`adb shell am start -W -a android.intent.action.VIEW -d "https://share.vyapari.link/s/<realId>"`
Expected: app opens; lands on the masjid detail (or feed if followed).
Until the host + `assetlinks.json` are live, the link opens a browser disambiguation —
that is expected and does not block the merge.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/AndroidManifest.xml
git commit -m "feat(deeplink): Android App Links intent-filter for /s/*"
```

---

### Task 13: iOS Universal Links entitlement

**Files:**
- Create: `ios/Runner/Runner.entitlements`
- Modify: `ios/Runner.xcodeproj/project.pbxproj` (`CODE_SIGN_ENTITLEMENTS` in the 3 build configs — Debug, Release, Profile)

**Interfaces:** none (native config).

- [ ] **Step 1: Create `ios/Runner/Runner.entitlements`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.developer.associated-domains</key>
	<array>
		<string>applinks:share.vyapari.link</string>
	</array>
</dict>
</plist>
```

- [ ] **Step 2: Reference it from the Xcode project**

In `ios/Runner.xcodeproj/project.pbxproj`, in each of the `Debug`, `Release`, `Profile`
`buildSettings` for the **Runner** target (search `PRODUCT_BUNDLE_IDENTIFIER = com.starkinnovations.m360;`
— the app target, not `RunnerTests`), add:

```
				CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;
```

- [ ] **Step 3: Verify project still parses**

Run: `cd ios && xcodebuild -list -project Runner.xcodeproj` (macOS) — should list schemes with no parse error. If `xcodebuild` is unavailable, run `plutil -lint Runner/Runner.entitlements` and open the project once in Xcode to confirm the entitlement shows under Signing & Capabilities → Associated Domains.

- [ ] **Step 4: Commit**

```bash
git add ios/Runner/Runner.entitlements ios/Runner.xcodeproj/project.pbxproj
git commit -m "feat(deeplink): iOS associated-domains entitlement for Universal Links"
```

---

### Task 14: Swap the shared Mux URL for the share-page URL

**Files:**
- Modify: `lib/services/api_services/broadcast_service.dart` (add `shareUrlFor`)
- Modify: `lib/features/home/screens/broadcast/broadcast_feed.dart:346-358` (`_shareMessage`)
- Modify: `lib/features/home/widgets/broadcast_message_card.dart` (add `messageId` field; use it in `_share` at line ~584)
- Modify: `lib/features/home/screens/broadcast/broadcast_feed.dart:~398` (pass `messageId: msg.id` where the card is built)
- Modify: `lib/features/home/screens/masjid/masjid_broadcast.dart:645` (`_sharePost`)
- Test: `test/share_url_test.dart`

**Interfaces:**
- Consumes: `dotenv.env['SHARE_BASE_URL']`.
- Produces: `String BroadcastService.shareUrlFor(String messageId)` →
  `"{SHARE_BASE_URL trimmed of trailing /}/s/{messageId}"`, default host if env missing.

- [ ] **Step 1: Write the failing test**

```dart
// test/share_url_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:m360/services/api_services/broadcast_service.dart';

void main() {
  test('shareUrlFor builds /s/{id}', () {
    dotenv.testLoad(fileInput: 'SHARE_BASE_URL=https://share.vyapari.link\n');
    expect(
      BroadcastService.instance.shareUrlFor('m1'),
      'https://share.vyapari.link/s/m1',
    );
  });

  test('shareUrlFor trims trailing slash', () {
    dotenv.testLoad(fileInput: 'SHARE_BASE_URL=https://share.vyapari.link/\n');
    expect(BroadcastService.instance.shareUrlFor('m1'),
        'https://share.vyapari.link/s/m1');
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/share_url_test.dart`
Expected: FAIL — `shareUrlFor` undefined

- [ ] **Step 3: Add `shareUrlFor` to `BroadcastService`**

```dart
  String shareUrlFor(String messageId) {
    final base = (dotenv.env['SHARE_BASE_URL'] ?? 'https://share.vyapari.link')
        .replaceAll(RegExp(r'/+$'), '');
    return '$base/s/$messageId';
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/share_url_test.dart`
Expected: PASS

- [ ] **Step 5: Update `broadcast_feed.dart` `_shareMessage`**

```dart
  void _shareMessage(BroadcastMessage msg) {
    AnalyticsService.instance.trackShareAnnouncement();
    final l10n = AppLocalizations.of(context);
    final text = msg.text.isNotEmpty
        ? msg.text
        : (l10n?.broadcast_share_default_text(widget.masjidName) ??
            'Check out this announcement from ${widget.masjidName} on Muslim360');
    final url = BroadcastService.instance.shareUrlFor(msg.id);
    Share.share('$text\n\n$url');
  }
```

(Delete the old `if (msg.videoUrl…) Share.share('$text\n\n${msg.videoUrl}')` branch — always share the page URL now.)

- [ ] **Step 6: Update `broadcast_message_card.dart`**

Add to the widget: `final String messageId;` and `required this.messageId,` in the
constructor. In `_share`:

```dart
  void _share(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final shareText = widget.text.isNotEmpty
        ? widget.text
        : (l10n?.broadcast_share_generic_text ??
            'Check out this announcement on Muslim360');
    final url = BroadcastService.instance.shareUrlFor(widget.messageId);
    await Share.share('$shareText\n\n$url');
  }
```

Add `import 'package:m360/services/api_services/broadcast_service.dart';` if absent.

- [ ] **Step 7: Pass `messageId` where the card is constructed**

In `broadcast_feed.dart` where `BroadcastMessageCard(...)` is built (near line 398, the
`onShare:` wiring), add `messageId: msg.id,`.

- [ ] **Step 8: Update `masjid_broadcast.dart` `_sharePost`**

```dart
void _sharePost(_BroadcastPost post) {
  final base = post.description ?? post.title ?? post.senderName;
  // NOTE: this screen still renders sample data; post.id is a local sample id.
  // Once it is backed by the real broadcast API, this shares a working link.
  final url = BroadcastService.instance.shareUrlFor(post.id);
  Share.share('$base\n\n$url');
}
```

Add the `BroadcastService` import if absent.

- [ ] **Step 9: Analyze + test + build**

Run: `flutter analyze lib/features/home/screens/broadcast/broadcast_feed.dart lib/features/home/widgets/broadcast_message_card.dart lib/features/home/screens/masjid/masjid_broadcast.dart`
Run: `flutter test`
Run: `flutter build apk --debug --dart-define=ENV=.env.dev`
Expected: analyze clean (pre-existing warnings aside), all tests PASS, build OK

- [ ] **Step 10: Commit**

```bash
git add lib/services/api_services/broadcast_service.dart lib/features/home/screens/broadcast/broadcast_feed.dart lib/features/home/widgets/broadcast_message_card.dart lib/features/home/screens/masjid/masjid_broadcast.dart test/share_url_test.dart
git commit -m "feat(share): share the web page URL instead of the raw Mux link"
```

---

### Task 15: End-to-end manual verification checklist

**Files:** none — this task produces a short report appended to the plan's PR description.

- [ ] **Step 1: Deploy the backend branch** to a host reachable at the configured
  `SHARE_WEB_BASE_URL`; set `ANDROID_SHA256_CERT_FINGERPRINTS` (from
  `keytool -list -v -keystore <release.keystore>`) and `APPLE_TEAM_ID`.

- [ ] **Step 2: Association files**
  - `curl https://<host>/.well-known/assetlinks.json` → valid JSON, correct package + fingerprint
  - `curl https://<host>/.well-known/apple-app-site-association` → `Content-Type: application/json`, correct `appID`
  - Paste the site into Google's Statement List Tester → passes

- [ ] **Step 3: Rich preview** — paste `https://<host>/s/<realId>` into WhatsApp, X, and
  iMessage → card shows the Mux thumbnail + masjid name + announcement text.

- [ ] **Step 4: Web page** — open the URL in mobile Chrome + Safari → video plays on tap;
  "Follow Masjid" opens the app (installed) or the store (not installed); "Share" invokes
  the native sheet.
  - [ ] verify iOS + desktop "Follow Masjid" CTA reaches the correct store

- [ ] **Step 5: Deep link, app installed + masjid followed** → lands on the broadcast feed;
  Back → masjid detail → Back → masjid list (Masjid tab).

- [ ] **Step 6: Deep link, app installed + masjid NOT followed** → lands on masjid detail
  with the "Add to My Masjid / Follow" prompt; Back → masjid list.

- [ ] **Step 7: Deep link, logged out** → login screen → after login, re-resolves to the
  masjid detail/feed.

- [ ] **Step 8: Deep link, app not installed** → store; after install, app opens to normal
  home (best-effort — target not preserved, as designed).

- [ ] **Step 9: Record results** in the PR description for each repo; open the two PRs
  (`feat/broadcast-share-deeplink` → `main` for backend, → `v3` for flutter).

---

## Self-Review

**Spec coverage:**

| Spec section | Task(s) |
| --- | --- |
| 5.1 share router + `.well-known` | 1, 4 |
| 5.2 public payload extension | 3 |
| 5.2 SharePageContext | 2 |
| 5.3 share.html template | 4 |
| 5.4 meta tags | 4 (asserted in test) |
| 5.5 smart app-open JS | 4 (in template) |
| 5.6 `.well-known` payloads | 1 |
| 5.7 config | 1, 5 |
| 5.8 factory wiring | 1 |
| 6.1 `app_links` dep | 6 |
| 6.2 Android manifest | 12 |
| 6.3 iOS entitlement | 13 |
| 6.4 DeepLinkService | 10, 11 |
| 6.5 main.dart | 11 |
| 6.6 BottomNav initialIndex | 9 |
| 6.7 replace Mux link | 14 |
| 7 isolation (`parseShareLink`, context builder) | 2, 7 |
| 8 error handling | 4 (404), 10 (snackbar/queue/login) |
| 9 testing | every task's test steps + 15 |
| 10 rollout | task order + phase gate + 15 |

**Placeholder scan:** the two Flutter tasks (10, 9) carry explicit "verify field names / swap test style if it doesn't compile" notes rather than guesses, because the exact `MasjidEntity` flag for "announcements enabled" and the cleanest `BottomNav` test harness can only be pinned down with the files open. All code blocks are complete and runnable as written; the notes are fallbacks, not gaps.

**Type consistency:** `PublicBroadcast` fields (Task 8) — `messageId, masjidId, masjidName, masjidPlaceId, masjidPhotoUrl, masjidVerified` — used identically in Task 10. `NavPlan{needsLogin, openFeed}` defined and consumed in Task 10 only. `parseShareMessageId(Uri, {shareHost})` defined Task 7, called Task 10. `build_share_context(message, masjid, settings)` defined Task 2, called Task 4. `Settings.share_host` / `.android_sha256_cert_fingerprints` / `.apple_app_id` defined Task 1, used Tasks 1/2/4. `BottomNav({initialIndex})` defined Task 9, used by `routes.dart` in Task 9 and relied on by Task 10's `pushNamedAndRemoveUntil(..., arguments: {'tab':'masjid'})`.
