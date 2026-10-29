# Share Analytics & Attribution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the announcement-sharing funnel (share → landing → playback → masjid) with Mixpanel, using backend-issued share links and a journey id that survives into the app.

**Architecture:** The backend owns a `shares` collection and mints tracked URLs. The share page and embed player emit Mixpanel events with attribution read from the URL (and, in the app WebView, the URL fragment). The Flutter app mints child shares on its Share CTA and emits the deep-link-opened event.

**Tech Stack:** FastAPI + PyMongo + Jinja2 (backend), Mixpanel JS (web), Flutter + `mixpanel_flutter` (app), pytest, `node:test`, `flutter_test`.

**Spec:** `docs/superpowers/specs/2026-10-29-share-analytics-design.md`

## Global Constraints

- Event names/attributes come verbatim from `docs/M360 - app events.csv`.
- `video_id` = announcement id (`message_id`).
- Mixpanel is the destination for these events; Firebase Analytics code stays untouched.
- Analytics must never block or break the user journey — all calls are fire-and-forget.
- Empty `MIXPANEL_TOKEN` disables everything (no-op, no errors).
- Share links are only minted for announcements whose `resolve_share_state(message) == "available"`.
- No secrets in templates beyond the Mixpanel project token (public by design).

---

## Phase 1 — Backend share registry

Work in `m360-backend`, branch `feat/share-analytics`.

### Task 1: Settings, request schema, and share repository

**Files:**
- Modify: `app/core/config.py` (after `mux_env_key`)
- Create: `app/schemas/share.py`
- Create: `app/interfaces/share_repository.py`
- Create: `app/repositories/mongo_share_repository.py`
- Test: `tests/test_share_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ShareCreateRequest`, `ShareRepository`, `MongoShareRepository`, `Settings.mixpanel_token`, `Settings.mixpanel_api_host`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_schema.py
import pytest
from pydantic import ValidationError

from app.schemas.share import ShareCreateRequest


def test_share_request_accepts_valid_payload():
    req = ShareCreateRequest(
        message_id="m1",
        channel="web_native_share_sheet",
        platform="mobile_web",
    )
    assert req.parent_share_id is None
    assert req.utm_source is None


def test_share_request_rejects_unknown_channel():
    with pytest.raises(ValidationError):
        ShareCreateRequest(
            message_id="m1",
            channel="whatsapp",
            platform="mobile_web",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_schema.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.share'`

- [ ] **Step 3: Create the schema**

```python
# app/schemas/share.py
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ShareChannel = Literal["android_native_share_sheet", "web_native_share_sheet"]
SharePlatform = Literal["android_app", "mobile_web", "desktop_web"]


class ShareCreateRequest(BaseModel):
    message_id: str = Field(min_length=1, max_length=64)
    parent_share_id: Optional[str] = Field(default=None, max_length=64)
    channel: ShareChannel
    platform: SharePlatform
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=120)
```

- [ ] **Step 4: Add settings**

```python
# app/core/config.py — immediately after mux_env_key
    mixpanel_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIXPANEL_TOKEN", "mixpanel_token"),
    )
    mixpanel_api_host: str = Field(
        default="https://api.mixpanel.com",
        validation_alias=AliasChoices("MIXPANEL_API_HOST", "mixpanel_api_host"),
    )
```

- [ ] **Step 5: Create the repository interface**

```python
# app/interfaces/share_repository.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ShareRepository(ABC):
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_by_share_id(self, share_id: str) -> Optional[Dict[str, Any]]:
        pass
```

- [ ] **Step 6: Create the Mongo repository**

```python
# app/repositories/mongo_share_repository.py
from __future__ import annotations

from typing import Any, Dict, Optional

from pymongo import ASCENDING
from pymongo.database import Database

from app.interfaces.share_repository import ShareRepository


class MongoShareRepository(ShareRepository):
    def __init__(self, db: Database) -> None:
        self._col = db["shares"]
        self._col.create_index([("share_id", ASCENDING)], unique=True)
        self._col.create_index([("message_id", ASCENDING), ("created_at", ASCENDING)])
        self._col.create_index([("root_share_id", ASCENDING)])

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data)
        self._col.insert_one(payload)
        payload.pop("_id", None)
        return payload

    def get_by_share_id(self, share_id: str) -> Optional[Dict[str, Any]]:
        if not share_id:
            return None
        doc = self._col.find_one({"share_id": share_id}, {"_id": 0})
        return dict(doc) if doc else None
```

- [ ] **Step 7: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS (existing suite + 2 new)

- [ ] **Step 8: Commit**

```bash
git add app/core/config.py app/schemas/share.py app/interfaces/share_repository.py app/repositories/mongo_share_repository.py tests/test_share_schema.py
git commit -m "feat(share): add share registry model, schema and repository"
```

---

### Task 2: ShareService — chain logic and tracked URL

**Files:**
- Create: `app/services/share_service.py`
- Test: `tests/test_share_service.py`

**Interfaces:**
- Consumes: `ShareRepository.create`, `ShareRepository.get_by_share_id`; `BroadcastFeedService.get_message_raw`; `resolve_share_state`; `Settings.share_web_base_url`.
- Produces: `ShareService.create_share(*, message_id, parent_share_id=None, channel, platform, user_id=None, utm_source=None, utm_medium=None, utm_campaign=None) -> dict`, and `ShareService.get_share(share_id) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_share_service.py
import pytest

from app.core.config import Settings
from app.exceptions.base import ApiException
from app.services.share_service import ShareService

MESSAGE = {
    "id": "m1",
    "masjid_id": "place1",
    "masjid_name": "Masjid Al Noor",
    "mux_playback_id": "pb1",
    "allow_sharing": True,
}


class _Repo:
    def __init__(self):
        self.docs = {}

    def create(self, data):
        self.docs[data["share_id"]] = dict(data)
        return dict(data)

    def get_by_share_id(self, share_id):
        return self.docs.get(share_id)


class _Feed:
    def __init__(self, message=None):
        self.message = message

    def get_message_raw(self, message_id):
        if self.message is None:
            raise ApiException("Broadcast not found", status_code=404)
        return self.message


def _service(message=None):
    return ShareService(
        share_repo=_Repo(),
        feed_service=_Feed(message if message is not None else dict(MESSAGE)),
        settings=Settings(share_web_base_url="https://muslim360.in"),
    )


def test_new_share_is_its_own_root():
    svc = _service()
    out = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    assert out["root_share_id"] == out["share_id"]
    assert out["parent_share_id"] is None
    assert out["url"].startswith("https://muslim360.in/s/m1?share=")


def test_child_share_inherits_root_and_parent():
    svc = _service()
    root = svc.create_share(
        message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
    )
    child = svc.create_share(
        message_id="m1",
        parent_share_id=root["share_id"],
        channel="android_native_share_sheet",
        platform="android_app",
    )
    assert child["root_share_id"] == root["share_id"]
    assert child["parent_share_id"] == root["share_id"]


def test_parent_from_another_message_is_rejected():
    svc = _service()
    other = svc.create_share(
        message_id="m2", channel="web_native_share_sheet", platform="mobile_web"
    )
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1",
            parent_share_id=other["share_id"],
            channel="web_native_share_sheet",
            platform="mobile_web",
        )
    assert err.value.status_code == 422


def test_sharing_disabled_is_rejected():
    svc = _service({**MESSAGE, "allow_sharing": False})
    with pytest.raises(ApiException) as err:
        svc.create_share(
            message_id="m1", channel="web_native_share_sheet", platform="mobile_web"
        )
    assert err.value.status_code == 409


def test_utm_params_are_appended_to_the_url():
    svc = _service()
    out = svc.create_share(
        message_id="m1",
        channel="web_native_share_sheet",
        platform="mobile_web",
        utm_source="whatsapp",
        utm_medium="social",
    )
    assert "utm_source=whatsapp" in out["url"]
    assert "utm_medium=social" in out["url"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_share_service.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.share_service'`

- [ ] **Step 3: Implement the service**

```python
# app/services/share_service.py
from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from app.core.config import Settings
from app.exceptions.base import ApiException
from app.interfaces.share_repository import ShareRepository
from app.utils.broadcast import resolve_share_state


class ShareService:
    def __init__(self, share_repo: ShareRepository, feed_service, settings: Settings) -> None:
        self._repo = share_repo
        self._feed = feed_service
        self._settings = settings

    def get_share(self, share_id: str) -> Optional[Dict[str, Any]]:
        if not share_id:
            return None
        return self._repo.get_by_share_id(share_id)

    def create_share(
        self,
        *,
        message_id: str,
        channel: str,
        platform: str,
        parent_share_id: Optional[str] = None,
        user_id: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
    ) -> Dict[str, Any]:
        message = self._feed.get_message_raw(message_id)
        if resolve_share_state(message) != "available":
            raise ApiException(
                "This announcement can no longer be shared",
                status_code=HTTPStatus.CONFLICT,
            )

        parent = None
        if parent_share_id:
            parent = self._repo.get_by_share_id(parent_share_id)
            if parent is None:
                raise ApiException("Share link not found", status_code=HTTPStatus.NOT_FOUND)
            if str(parent.get("message_id")) != str(message_id):
                raise ApiException(
                    "Share link does not belong to this announcement",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

        share_id = str(uuid.uuid4())
        root_share_id = (parent or {}).get("root_share_id") or share_id
        record = {
            "share_id": share_id,
            "message_id": str(message_id),
            "masjid_id": str(message.get("masjid_id") or ""),
            "masjid_name": str(message.get("masjid_name") or ""),
            "video_id": str(message_id),
            "mux_playback_id": message.get("mux_playback_id"),
            "root_share_id": root_share_id,
            "parent_share_id": parent_share_id,
            "created_by_user_id": user_id,
            "channel": channel,
            "platform": platform,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "created_at": _now_iso(),
        }
        self._repo.create(record)
        record["url"] = self._build_url(
            message_id, share_id, utm_source, utm_medium, utm_campaign
        )
        return record

    def _build_url(
        self,
        message_id: str,
        share_id: str,
        utm_source: Optional[str],
        utm_medium: Optional[str],
        utm_campaign: Optional[str],
    ) -> str:
        base = self._settings.share_web_base_url.rstrip("/")
        params: Dict[str, str] = {"share": share_id}
        if utm_source:
            params["utm_source"] = utm_source
        if utm_medium:
            params["utm_medium"] = utm_medium
        if utm_campaign:
            params["utm_campaign"] = utm_campaign
        return f"{base}/s/{message_id}?{urlencode(params)}"
```

Add this helper at the top of the module:

```python
def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests/test_share_service.py -q`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/services/share_service.py tests/test_share_service.py
git commit -m "feat(share): mint tracked share links with root/parent chain"
```

---

### Task 3: `POST /api/v1/shares` endpoint and wiring

**Files:**
- Create: `app/api/v1/endpoints/shares.py`
- Modify: `app/api/v1/router.py`
- Modify: `app/api/deps.py` (add `get_share_service`)
- Modify: `app/bootstrap.py` (wire `app.state.share_service`)
- Test: `tests/test_share_endpoint.py`

**Interfaces:**
- Consumes: `ShareCreateRequest`, `ShareService.create_share`.
- Produces: HTTP `POST /api/v1/shares` → `201 {"status","message","data":{share_id,root_share_id,parent_share_id,url}}`; `get_share_service(request)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_endpoint.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_share_service
from app.api.v1.endpoints import shares


class _Svc:
    def __init__(self, result=None):
        self.result = result or {
            "share_id": "s1",
            "root_share_id": "s1",
            "parent_share_id": None,
            "url": "https://muslim360.in/s/m1?share=s1",
        }
        self.kwargs = None

    def create_share(self, **kwargs):
        self.kwargs = kwargs
        return self.result


def _client(svc):
    app = FastAPI()
    app.include_router(shares.router)
    app.dependency_overrides[get_share_service] = lambda: svc
    return TestClient(app)


def test_create_share_returns_tracked_url():
    svc = _Svc()
    resp = _client(svc).post(
        "/shares",
        json={
            "message_id": "m1",
            "channel": "web_native_share_sheet",
            "platform": "mobile_web",
        },
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["share_id"] == "s1"
    assert body["url"].endswith("?share=s1")
    assert svc.kwargs["channel"] == "web_native_share_sheet"


def test_create_share_validates_payload():
    resp = _client(_Svc()).post("/shares", json={"message_id": "m1"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_endpoint.py -q`
Expected: FAIL — `ImportError: cannot import name 'shares'`

- [ ] **Step 3: Create the endpoint**

```python
# app/api/v1/endpoints/shares.py
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_optional_current_user, get_share_service
from app.schemas.share import ShareCreateRequest
from app.utils.response import success_response

router = APIRouter(tags=["Shares"])


@router.post("/shares", summary="Create a tracked share link")
def create_share(
    payload: ShareCreateRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    svc=Depends(get_share_service),
):
    user_id = current_user["user_id"] if current_user else None
    data = svc.create_share(
        message_id=payload.message_id,
        parent_share_id=payload.parent_share_id,
        channel=payload.channel,
        platform=payload.platform,
        user_id=user_id,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
    )
    return success_response(data, message="Share link created", status_code=201)
```

- [ ] **Step 4: Add the dependency**

```python
# app/api/deps.py
def get_share_service(request: Request):
    return getattr(request.app.state, "share_service", None)
```

- [ ] **Step 5: Register the router**

In `app/api/v1/router.py`, add `shares` to the endpoint imports and include it after `broadcasts`:

```python
api_v1_router.include_router(shares.router)
```

- [ ] **Step 6: Wire the service in bootstrap**

Inside the `if mongo_client is not None:` block in `app/bootstrap.py`, after `app.state.broadcast_feed_service` is created:

```python
        from app.repositories.mongo_share_repository import MongoShareRepository
        from app.services.share_service import ShareService

        app.state.share_service = ShareService(
            share_repo=MongoShareRepository(db),
            feed_service=app.state.broadcast_feed_service,
            settings=settings,
        )
```

In the `else:` branch add:

```python
        app.state.share_service = None
```

- [ ] **Step 7: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add app/api/v1/endpoints/shares.py app/api/v1/router.py app/api/deps.py app/bootstrap.py tests/test_share_endpoint.py
git commit -m "feat(api): add POST /shares"
```

---

### Task 4: Share attribution on the landing page

**Files:**
- Modify: `app/web/share_context.py` (`video_id`, analytics config, attribution fields)
- Modify: `app/web/share.py` (`/s/` reads `?share` and UTM)
- Test: `tests/test_share_context.py`, `tests/test_share_template.py`

**Interfaces:**
- Consumes: `ShareService.get_share`.
- Produces: template context keys `video_id`, `share_id`, `root_share_id`, `parent_share_id`, `utm_source`, `utm_medium`, `utm_campaign`, `mixpanel_token`, `mixpanel_api_host`.

- [ ] **Step 1: Write the failing context test**

```python
# tests/test_share_context.py
def test_analytics_context_includes_video_and_ids():
    from app.core.config import Settings
    from app.web.share_context import build_share_context

    msg = {
        "id": "m1",
        "text": "S",
        "created_at": "2026-10-13T10:00:00+00:00",
        "mux_playback_id": "pb1",
    }
    ctx = build_share_context(
        msg,
        {"name": "Masjid", "place_id": "ChIJx"},
        Settings(mixpanel_token="mp-token"),
        share_attribution={
            "share_id": "s1",
            "root_share_id": "s0",
            "parent_share_id": "",
            "utm_source": "whatsapp",
        },
    )
    assert ctx["video_id"] == "m1"
    assert ctx["share_id"] == "s1"
    assert ctx["root_share_id"] == "s0"
    assert ctx["utm_source"] == "whatsapp"
    assert ctx["mixpanel_token"] == "mp-token"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_context.py::test_analytics_context_includes_video_and_ids -q`
Expected: FAIL — `TypeError: build_share_context() got an unexpected keyword argument 'share_attribution'`

- [ ] **Step 3: Extend the context builder**

In `app/web/share_context.py`:

1. Add the parameter `share_attribution: Optional[dict] = None`.
2. Before the return, add:

```python
    attribution = share_attribution or {}
```

(`message_id` is already computed at the top of the function — reuse it.)

3. Add these keys to the returned dict:

```python
        "video_id": message_id,
        "share_id": str(attribution.get("share_id") or ""),
        "root_share_id": str(attribution.get("root_share_id") or ""),
        "parent_share_id": str(attribution.get("parent_share_id") or ""),
        "utm_source": str(attribution.get("utm_source") or ""),
        "utm_medium": str(attribution.get("utm_medium") or ""),
        "utm_campaign": str(attribution.get("utm_campaign") or ""),
        "mixpanel_token": settings.mixpanel_token or "",
        "mixpanel_api_host": settings.mixpanel_api_host,
```

- [ ] **Step 4: Read `?share` in the route**

In `app/web/share.py`, add `share_svc=Depends(get_share_service)` to `share_page`, then before rendering:

```python
    attribution = _share_attribution(request, share_svc)
    ctx.update(attribution)
```

And add this module-level helper:

```python
def _share_attribution(request: Request, share_svc) -> dict:
    sid = (request.query_params.get("share") or "").strip()
    record = None
    if sid and share_svc is not None:
        try:
            record = share_svc.get_share(sid)
        except Exception:
            record = None
    record = record or {}
    return {
        "share_id": str(record.get("share_id") or ""),
        "root_share_id": str(record.get("root_share_id") or ""),
        "parent_share_id": str(record.get("parent_share_id") or ""),
        "utm_source": request.query_params.get("utm_source") or str(record.get("utm_source") or ""),
        "utm_medium": request.query_params.get("utm_medium") or str(record.get("utm_medium") or ""),
        "utm_campaign": request.query_params.get("utm_campaign") or str(record.get("utm_campaign") or ""),
    }
```

Pass it into `build_share_context(..., share_attribution=attribution)`.

- [ ] **Step 5: Add the unknown-share test**

Add this helper next to `_embed_client` in `tests/test_share_template.py`:

```python
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
```

Add `get_masjid_search_service` and `get_share_service` to the imports, then:

```python
def test_share_page_tolerates_unknown_share_id():
    client = _share_client(
        message=_video_message(), masjid={"name": "Masjid Al Noor"}, share_svc=None
    )
    resp = client.get("/s/m1?share=does-not-exist")
    assert resp.status_code == 200
    assert "Masjid Al Noor" in resp.text
```

- [ ] **Step 6: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/web/share_context.py app/web/share.py tests/test_share_context.py tests/test_share_template.py
git commit -m "feat(share): expose share attribution to the landing page"
```

---

### Task 5: Privacy policy mentions Mixpanel

**Files:**
- Modify: `app/web/templates/privacy.html`
- Test: `tests/test_privacy_page.py`

**Interfaces:** none.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_privacy_page.py
def test_privacy_page_mentions_mixpanel_analytics():
    from app.web.templating import env

    html = env.get_template("privacy.html").render()
    assert "Mixpanel" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_privacy_page.py::test_privacy_page_mentions_mixpanel_analytics -q`
Expected: FAIL

- [ ] **Step 3: Update the copy**

In `privacy.html`:
- In “d. App Usage & Diagnostics”, add a bullet: “Anonymous product events (for example, video playback milestones) through Mixpanel.”
- In “3. Data Sharing”, add a bullet: “Mixpanel processes anonymous product events on our behalf; no advertising identifiers are sent.”
- Change the date to “Last updated: 29th October 2026”.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/web/templates/privacy.html tests/test_privacy_page.py
git commit -m "docs(privacy): disclose Mixpanel product analytics"
```

---

## Phase 2 — Web analytics

All work continues in `m360-backend`.

### Task 6: Analytics module with testable milestones

**Files:**
- Create: `app/web/static/m360-analytics.js`
- Test: `tests/js/m360_analytics.test.js`

**Interfaces:**
- Produces (browser global `M360Analytics` and CommonJS export):
  - `nextMilestone(prevMark: number, position: number, duration: number): number | null`
  - `visitorId(): string`
  - `init(config: {token, apiHost, base: object}): void`
  - `track(event: string, props?: object): void`
  - `setupPlayer(video: HTMLVideoElement, base: object): void`

- [ ] **Step 1: Write the failing test**

```javascript
// tests/js/m360_analytics.test.js
const test = require('node:test');
const assert = require('node:assert');
const { nextMilestone } = require('../../app/web/static/m360-analytics.js');

test('returns 25 when crossing the first mark', () => {
  assert.equal(nextMilestone(0, 26, 100), 25);
});

test('skips marks already passed', () => {
  assert.equal(nextMilestone(25, 60, 100), 50);
});

test('returns null below the next mark', () => {
  assert.equal(nextMilestone(25, 30, 100), null);
});

test('returns null when duration is unknown', () => {
  assert.equal(nextMilestone(0, 10, 0), null);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the module**

```javascript
// app/web/static/m360-analytics.js
(function (global) {
  'use strict';

  var MARKS = [25, 50, 75];
  var client = null;
  var base = {};
  var visitor = null;

  function nextMilestone(prevMark, position, duration) {
    if (!duration || duration <= 0) return null;
    var pct = (position / duration) * 100;
    for (var i = 0; i < MARKS.length; i++) {
      var m = MARKS[i];
      if (m > prevMark && pct >= m) return m;
    }
    return null;
  }

  function uuid() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'v-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  }

  function visitorId() {
    if (visitor) return visitor;
    try {
      var key = 'm360_visitor_id';
      var v = global.localStorage.getItem(key);
      if (!v) {
        v = uuid();
        global.localStorage.setItem(key, v);
      }
      visitor = v;
    } catch (e) {
      visitor = uuid();
    }
    return visitor;
  }

  function init(config) {
    if (!config || !config.token || typeof global.mixpanel === 'undefined') return;
    global.mixpanel.init(config.token, {
      api_host: config.apiHost || 'https://api.mixpanel.com',
      persistence: 'localStorage',
      track_pageview: false,
      autotrack: false,
    });
    client = global.mixpanel;
    base = config.base || {};
    base.anonymous_visitor_id = visitorId();
    client.register(base);
  }

  function track(event, props) {
    if (!client) return;
    try {
      client.track(event, props || {});
    } catch (e) {}
  }

  function setupPlayer(video, extra) {
    if (!video) return;
    var baseProps = Object.assign({}, base, extra || {});
    var mark = 0;
    var started = false;

    video.addEventListener('playing', function () {
      if (started) return;
      started = true;
      mark = 0;
      track('video_playback_started', Object.assign({}, baseProps, {
        mux_playback_id: baseProps.mux_playback_id || '',
        video_duration_seconds: video.duration || null,
      }));
    });

    video.addEventListener('timeupdate', function () {
      if (!started) return;
      var m = nextMilestone(mark, video.currentTime, video.duration);
      if (m === null) return;
      mark = m;
      track('video_playback_' + m + '_percent', Object.assign({}, baseProps, {
        playback_position_seconds: Math.round(video.currentTime),
        playback_percentage: m,
        video_duration_seconds: video.duration || null,
      }));
    });

    video.addEventListener('ended', function () {
      track('video_playback_completed', Object.assign({}, baseProps, {
        playback_position_seconds: Math.round(video.currentTime),
        playback_percentage: 100,
        video_duration_seconds: video.duration || null,
      }));
      started = false;
      mark = 0;
    });

    video.addEventListener('error', function () {
      track('video_playback_error', Object.assign({}, baseProps, {
        error_code: (video.error && video.error.code) || '',
        error_type: 'media_error',
        sanitized_error_message: 'Playback failed',
      }));
    });
  }

  var api = {
    nextMilestone: nextMilestone,
    visitorId: visitorId,
    init: init,
    track: track,
    setupPlayer: setupPlayer,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.M360Analytics = api;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/web/static/m360-analytics.js tests/js/m360_analytics.test.js
git commit -m "feat(web): add mixpanel analytics module with milestone logic"
```

---

### Task 7: Landing page events

**Files:**
- Modify: `app/web/templates/share.html`
- Test: `tests/test_share_template.py`

**Interfaces:**
- Consumes: `M360Analytics.init/track/setupPlayer`, context keys from Task 4.

- [ ] **Step 1: Write the failing template test**

```python
# tests/test_share_template.py
def test_share_template_includes_analytics_bootstrap():
    html = _render(mixpanel_token="mp-token")
    assert "M360_ANALYTICS_BASE" in html
    assert "m360-analytics.js" in html
    assert "video_landing_page_viewed" in html
```

Update `_render` defaults to add:

```python
        video_id="m1",
        share_id="",
        root_share_id="",
        parent_share_id="",
        utm_source="",
        utm_medium="",
        utm_campaign="",
        mixpanel_token="mp-token",
        mixpanel_api_host="https://api.mixpanel.com",
        mux_playback_id="pb1",
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_template.py::test_share_template_includes_analytics_bootstrap -q`
Expected: FAIL

- [ ] **Step 3: Wire the template**

In `share.html`, immediately before `</html>` — after the existing page script, so
`IS_ANDROID`/`IS_IOS` are already defined:

```html
<script src="https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js"></script>
<script src="/share-static/m360-analytics.js"></script>
<script>
  var M360_ANALYTICS_BASE = {
    video_id: {{ video_id | tojson }},
    video_title: {{ analytics_title | tojson }},
    masjid_id: {{ masjid_place_id | tojson }},
    masjid_name: {{ masjid_name | tojson }},
    mux_playback_id: {{ (mux_playback_id or "") | tojson }},
    share_id: {{ share_id | tojson }},
    root_share_id: {{ root_share_id | tojson }},
    parent_share_id: {{ parent_share_id | tojson }},
    utm_source: {{ utm_source | tojson }},
    utm_medium: {{ utm_medium | tojson }},
    utm_campaign: {{ utm_campaign | tojson }},
    platform: IS_ANDROID ? "mobile_web" : (IS_IOS ? "mobile_web" : "desktop_web")
  };
  M360Analytics.init({
    token: {{ mixpanel_token | tojson }},
    apiHost: {{ mixpanel_api_host | tojson }},
    base: M360_ANALYTICS_BASE
  });
  M360Analytics.track("video_landing_page_viewed", {});
</script>
```

In the existing `startMux`/`attachPlayer` flow, after the video element starts playing, call `M360Analytics.setupPlayer(v, {})` once (inside the `started` block, before `attachPlayer`).

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/web/templates/share.html tests/test_share_template.py
git commit -m "feat(share): emit landing and playback events"
```

---

### Task 8: `View Masjid` journey id and CTA event

**Files:**
- Modify: `app/web/templates/share.html`
- Test: `tests/test_share_template.py`

**Interfaces:**
- Consumes: `M360Analytics.track`.
- Produces: `?j=<journey_id>&s=<share_id>` on the follow deep link.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_template.py
def test_share_template_builds_journey_link():
    html = _render()
    assert "journey_id" in html
    assert "click_on_view_masjid_cta" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_template.py::test_share_template_builds_journey_link -q`
Expected: FAIL

- [ ] **Step 3: Implement**

Replace the `openApp()` entry so the Follow button handler first builds a journey:

```javascript
function newJourneyId() {
  if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
  return 'j-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
}

function followUrl() {
  var params = [];
  var journey = newJourneyId();
  params.push("j=" + encodeURIComponent(journey));
  if (M360_ANALYTICS_BASE.share_id) {
    params.push("s=" + encodeURIComponent(M360_ANALYTICS_BASE.share_id));
  }
  return "https://" + SHARE_HOST + FOLLOW_PATH + "?" + params.join("&");
}

function onFollowClick() {
  var url = followUrl();
  var journey = decodeURIComponent(url.split("j=")[1].split("&")[0]);
  M360Analytics.track("click_on_view_masjid_cta", {
    journey_id: journey,
    cta_destination: "masjid_detail"
  });
  openApp(url);
}
```

Change `openApp()` to accept `targetUrl` and use it in the `intent://`, iOS and fallback paths (`FOLLOW_DEEPLINK` becomes `targetUrl`). Update the button handler to `onFollowClick`.

The Play Store fallback must carry the same attribution, so build it per click instead of reusing the page-load `STORE_URL`:

```javascript
function storeUrlFor(targetUrl) {
  var referrer = "deeplink=" + encodeURIComponent(targetUrl);
  return PLAY_URL + (PLAY_URL.indexOf("?") >= 0 ? "&" : "?") +
    "referrer=" + encodeURIComponent(referrer);
}
```

Inside `openApp(targetUrl)`, use `var storeUrl = storeUrlFor(targetUrl);` everywhere the old code used `STORE_URL`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/web/templates/share.html tests/test_share_template.py
git commit -m "feat(share): tag View Masjid clicks with a journey id"
```

---

### Task 9: Web share CTA and Play Store redirect events

**Files:**
- Modify: `app/web/templates/share.html`
- Test: `tests/test_share_template.py`

**Interfaces:**
- Consumes: `POST /api/v1/shares`, `M360Analytics.track`.
- Produces: child share creation on web share; `redirect_to_play_store`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_template.py
def test_share_template_creates_child_share_and_tracks_redirect():
    html = _render()
    assert "click_on_share_announcement" in html
    assert "redirect_to_play_store" in html
    assert "/api/v1/shares" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_template.py::test_share_template_creates_child_share_and_tracks_redirect -q`
Expected: FAIL

- [ ] **Step 3: Implement**

Make `sharePage()` async and mint a child share first:

```javascript
async function createChildShare() {
  try {
    var res = await fetch("/api/v1/shares", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: {{ message_id | tojson }},
        parent_share_id: M360_ANALYTICS_BASE.share_id || null,
        channel: "web_native_share_sheet",
        platform: M360_ANALYTICS_BASE.platform
      })
    });
    if (!res.ok) return null;
    var body = await res.json();
    return body.data || null;
  } catch (e) {
    return null;
  }
}

async function sharePage() {
  var child = await createChildShare();
  var url = (child && child.url) ? child.url : PAGE_URL;
  M360Analytics.track("click_on_share_announcement", {
    share_id: (child && child.share_id) || "",
    root_share_id: (child && child.root_share_id) || "",
    parent_share_id: (child && child.parent_share_id) || "",
    share_channel: "web_native_share_sheet"
  });
  if (navigator.share) {
    navigator.share({ title: document.title, url: url }).catch(function () {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(function () {
      var t = document.getElementById("toast");
      t.classList.add("show");
      setTimeout(function () { t.classList.remove("show"); }, 1600);
    }).catch(function () {});
  } else {
    window.prompt("Copy link:", url);
  }
}
```

Before every `window.location = STORE_URL` (Android timer, Chrome fallback, desktop branch), add:

```javascript
M360Analytics.track("redirect_to_play_store", {
  redirect_destination: "google_play_store",
  redirect_reason: "app_not_opened"
});
```

Use `"app_not_installed"` for the `browser_fallback_url` path if you cannot distinguish; a single reason per branch is acceptable.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/web/templates/share.html tests/test_share_template.py
git commit -m "feat(share): track web shares and store redirects"
```

---

### Task 10: In-app embed context and platform

**Files:**
- Modify: `app/web/templates/share_embed.html`
- Modify: `app/web/templates/_share_player.html`
- Test: `tests/test_share_template.py`

**Interfaces:**
- Consumes: `M360Analytics.init/track/setupPlayer`.
- Produces: playback events with `platform=android_app` and fragment-provided ids.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_share_template.py
def test_embed_template_includes_analytics_and_fragment_context():
    html = env.get_template("share_embed.html").render(**_embed_context())
    assert "m360-analytics.js" in html
    assert "M360_ANALYTICS_BASE" in html
    assert "location.hash" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_share_template.py::test_embed_template_includes_analytics_and_fragment_context -q`
Expected: FAIL

- [ ] **Step 3: Implement**

In `share_embed.html`, after the player include:

```html
<script src="https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js"></script>
<script src="/share-static/m360-analytics.js"></script>
<script>
  var M360_ANALYTICS_BASE = {
    video_id: {{ video_id | tojson }},
    video_title: {{ analytics_title | tojson }},
    masjid_id: {{ masjid_place_id | tojson }},
    masjid_name: {{ masjid_name | tojson }},
    mux_playback_id: {{ (mux_playback_id or "") | tojson }},
    share_id: "",
    root_share_id: "",
    parent_share_id: "",
    platform: "android_app"
  };
  (function () {
    var frag = new URLSearchParams((location.hash || "").replace(/^#/, ""));
    if (frag.get("s")) M360_ANALYTICS_BASE.share_id = frag.get("s");
    if (frag.get("j")) M360_ANALYTICS_BASE.journey_id = frag.get("j");
    if (frag.get("u")) M360_ANALYTICS_BASE.user_id = frag.get("u");
    if (frag.get("v")) M360_ANALYTICS_BASE.anonymous_visitor_id = frag.get("v");
    M360Analytics.init({
      token: {{ mixpanel_token | tojson }},
      apiHost: {{ mixpanel_api_host | tojson }},
      base: M360_ANALYTICS_BASE
    });
    var v = document.getElementById("v");
    if (v) M360Analytics.setupPlayer(v, {});
  })();
</script>
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/web/templates/share_embed.html app/web/templates/_share_player.html tests/test_share_template.py
git commit -m "feat(embed): emit playback analytics with in-app context"
```

---

## Phase 3 — Flutter app

Work in `m360-flutter-app`, branch `feat/share-analytics` (create from `v3`).

### Task 11: `mixpanel_flutter` and `MixpanelService`

**Files:**
- Modify: `pubspec.yaml`
- Create: `lib/services/mixpanel_service.dart`
- Modify: `lib/main.dart`
- Test: `test/mixpanel_service_test.dart`

**Interfaces:**
- Produces: `MixpanelService.instance.init()`, `MixpanelService.instance.track(String, [Map<String, dynamic>?])`, `MixpanelService.instance.visitorId`.

- [ ] **Step 1: Add the dependency**

Run: `flutter pub add mixpanel_flutter`
Expected: `pubspec.yaml` gains `mixpanel_flutter:` and `flutter pub get` resolves.

- [ ] **Step 2: Write the failing test**

```dart
// test/mixpanel_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/mixpanel_service.dart';

void main() {
  test('is a no-op before init', () {
    MixpanelService.instance.track('x', {'a': 1});
    expect(MixpanelService.instance.enabled, isFalse);
  });
}
```

- [ ] **Step 3: Run to verify it fails**

Run: `flutter test test/mixpanel_service_test.dart`
Expected: FAIL — `mixpanel_service.dart` not found

- [ ] **Step 4: Implement**

```dart
// lib/services/mixpanel_service.dart
import 'package:mixpanel_flutter/mixpanel_flutter.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'package:m360/services/analytics_base_params.dart';
import 'package:m360/services/store_manager.dart';

class MixpanelService {
  MixpanelService._();
  static final MixpanelService instance = MixpanelService._();

  Mixpanel? _client;

  bool get enabled => _client != null;

  String? get visitorId {
    final value = AnalyticsBaseParams.instance.current()['device_id'];
    return value is String ? value : null;
  }

  Future<void> init() async {
    final token = (dotenv.env['MIXPANEL_TOKEN'] ?? '').trim();
    if (token.isEmpty) return;
    try {
      await Mixpanel.init(token, trackAutomaticEvents: false);
      final deviceId = await AnalyticsBaseParams.instance.init();
      final client = Mixpanel.getInstance();
      await client.identify(deviceId);
      client.registerSuperProperties({
        'platform': 'android_app',
        'anonymous_visitor_id': deviceId,
      });
      _client = client;
    } catch (_) {
      _client = null;
    }
  }

  void track(String event, [Map<String, dynamic>? properties]) {
    final client = _client;
    if (client == null) return;
    try {
      final props = <String, dynamic>{...?properties};
      final userId = StoreManager.instance.userId;
      if (userId != null && userId.isNotEmpty) props['user_id'] = userId;
      client.track(event, properties: props);
    } catch (_) {}
  }
}
```

- [ ] **Step 5: Initialise in `main.dart`**

After `await AnalyticsService.instance.initializeUserId();` add:

```dart
  unawaited(MixpanelService.instance.init());
```

- [ ] **Step 6: Run tests**

Run: `flutter test test/mixpanel_service_test.dart`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pubspec.yaml pubspec.lock lib/services/mixpanel_service.dart lib/main.dart test/mixpanel_service_test.dart
git commit -m "feat(app): add Mixpanel service"
```

---

### Task 12: `BroadcastService.createShareLink`

**Files:**
- Modify: `lib/services/api_services/broadcast_service.dart`
- Test: `test/broadcast_share_link_test.dart`

**Interfaces:**
- Produces: `BroadcastService.createShareLink(String messageId, {String? parentShareId, String channel = 'android_native_share_sheet'}) -> Future<ShareLink?>`, class `ShareLink {shareId, rootShareId, parentShareId, url}`.

- [ ] **Step 1: Write the failing test**

```dart
// test/broadcast_share_link_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/api_services/broadcast_service.dart';

void main() {
  test('ShareLink parses the API payload', () {
    final link = ShareLink.fromJson({
      'share_id': 's1',
      'root_share_id': 's0',
      'parent_share_id': null,
      'url': 'https://muslim360.in/s/m1?share=s1',
    });
    expect(link.shareId, 's1');
    expect(link.rootShareId, 's0');
    expect(link.parentShareId, isNull);
    expect(link.url, contains('share=s1'));
  });
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `flutter test test/broadcast_share_link_test.dart`
Expected: FAIL — `ShareLink` undefined

- [ ] **Step 3: Implement**

```dart
// lib/services/api_services/broadcast_service.dart — top of file
class ShareLink {
  final String shareId;
  final String rootShareId;
  final String? parentShareId;
  final String url;

  const ShareLink({
    required this.shareId,
    required this.rootShareId,
    this.parentShareId,
    required this.url,
  });

  factory ShareLink.fromJson(Map<String, dynamic> json) => ShareLink(
        shareId: json['share_id'] as String? ?? '',
        rootShareId: json['root_share_id'] as String? ?? '',
        parentShareId: json['parent_share_id'] as String?,
        url: json['url'] as String? ?? '',
      );
}
```

Add the method to `BroadcastService`:

```dart
  Future<ShareLink?> createShareLink(
    String messageId, {
    String? parentShareId,
    String channel = 'android_native_share_sheet',
  }) async {
    try {
      final token = StoreManager.instance.accessToken;
      final api = ApiService(
        baseUrl: baseUrl,
        timeout: const Duration(seconds: 2),
        retries: 0,
        headers: token != null ? {'Authorization': 'Bearer $token'} : null,
      );
      final res = await api.post<Map<String, dynamic>>(
        '/shares',
        data: {
          'message_id': messageId,
          'parent_share_id': parentShareId,
          'channel': channel,
          'platform': 'android_app',
        },
      );
      if (res.statusCode != 201) return null;
      final data = res.data?['data'];
      if (data is! Map<String, dynamic>) return null;
      return ShareLink.fromJson(data);
    } catch (_) {
      return null;
    }
  }
```

- [ ] **Step 4: Run tests**

Run: `flutter test test/broadcast_share_link_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/services/api_services/broadcast_service.dart test/broadcast_share_link_test.dart
git commit -m "feat(app): add createShareLink API call"
```

---

### Task 13: Track and attribute the app Share CTA

**Files:**
- Modify: `lib/features/home/widgets/broadcast_message_card.dart`
- Modify: `lib/services/deep_link_service.dart` (remember incoming share/journey)
- Modify: `lib/features/home/widgets/broadcast_message_card.dart` import section
- Test: `test/broadcast_share_attribution_test.dart`

**Interfaces:**
- Consumes: `BroadcastService.createShareLink`, `MixpanelService.track`, `DeepLinkService.currentShareId`.
- Produces: no new API; emits `click_on_share_announcement`.

- [ ] **Step 1: Add incoming-context fields**

In `DeepLinkService`:

```dart
  String? currentShareId;
  String? currentJourneyId;
```

At the top of `handleUri` (after the repeat check):

```dart
    final query = uri.queryParameters;
    currentShareId = query['s'] ?? query['share'];
    currentJourneyId = query['j'];
```

Clear them in `debugReset()`.

- [ ] **Step 2: Write the failing test**

```dart
// test/broadcast_share_attribution_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/deep_link_service.dart';

void main() {
  test('deep link stores share and journey ids', () async {
    DeepLinkService.instance.debugReset();
    expect(DeepLinkService.instance.currentShareId, isNull);
    await DeepLinkService.instance.handleUri(
      Uri.parse('https://muslim360.in/m/ChIJx?j=j1&s=s1'),
    );
    expect(DeepLinkService.instance.currentShareId, 's1');
    expect(DeepLinkService.instance.currentJourneyId, 'j1');
  });
}
```

- [ ] **Step 3: Run to verify it fails**

Run: `flutter test test/broadcast_share_attribution_test.dart`
Expected: FAIL

- [ ] **Step 4: Implement the share flow**

In `broadcast_message_card.dart`, replace the body of `_share`:

```dart
  void _share(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final shareText = widget.text.isNotEmpty
        ? widget.text
        : (l10n?.broadcast_share_generic_text ?? 'Check out this announcement on Muslim360');
    final link = await BroadcastService.instance.createShareLink(
      widget.messageId,
      parentShareId: DeepLinkService.instance.currentShareId,
    );
    final url = (link != null && link.url.isNotEmpty)
        ? link.url
        : BroadcastService.instance.shareUrlFor(widget.messageId);

    MixpanelService.instance.track('click_on_share_announcement', {
      'video_id': widget.messageId,
      'video_title': widget.text,
      'masjid_id': widget.masjidId,
      'masjid_name': widget.masjidName,
      'share_id': link?.shareId ?? '',
      'root_share_id': link?.rootShareId ?? '',
      'parent_share_id': link?.parentShareId ?? '',
      'share_channel': 'android_native_share_sheet',
      'platform': 'android_app',
    });

    await Share.share('$shareText\n\n$url');
  }
```

Add `masjidId` and `masjidName` to the card (neither exists yet):

```dart
// lib/features/home/widgets/broadcast_message_card.dart — fields
  final String masjidId;
  final String masjidName;

// constructor
    required this.masjidId,
    required this.masjidName,
```

At the call site in `lib/features/home/screens/broadcast/broadcast_feed.dart` (both values already live on the feed widget):

```dart
    return BroadcastMessageCard(
      masjidId: widget.masjidId,
      masjidName: widget.masjidName,
      messageId: msg.id,
      // …existing arguments unchanged
```

Add imports:
```dart
import 'package:m360/services/deep_link_service.dart';
import 'package:m360/services/mixpanel_service.dart';
```

- [ ] **Step 5: Run tests**

Run: `flutter test test/broadcast_share_attribution_test.dart test/broadcast_share_ui_test.dart`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add lib/services/deep_link_service.dart lib/features/home/widgets/broadcast_message_card.dart test/broadcast_share_attribution_test.dart
git commit -m "feat(app): track share clicks with inherited share id"
```

---

### Task 14: `masjid_deep_link_opened`

**Files:**
- Modify: `lib/services/deep_link_service.dart`
- Test: `test/deep_link_service_navigation_test.dart`

**Interfaces:**
- Consumes: `MixpanelService.track`.

- [ ] **Step 1: Write the failing test**

Extend the existing logged-out PDP test to assert the event was tracked. Use a small test seam:

```dart
// lib/services/mixpanel_service.dart — replace the existing track method
  @visibleForTesting
  void Function(String event, Map<String, dynamic> props)? trackOverride;

  void track(String event, [Map<String, dynamic>? properties]) {
    final props = <String, dynamic>{...?properties};
    final userId = StoreManager.instance.userId;
    if (userId != null && userId.isNotEmpty) props['user_id'] = userId;

    final override = trackOverride;
    if (override != null) {
      override(event, props);
      return;
    }

    final client = _client;
    if (client == null) return;
    try {
      client.track(event, properties: props);
    } catch (_) {}
  }
```

Then in `test/deep_link_service_navigation_test.dart`:

```dart
    final events = <String>[];
    MixpanelService.instance.trackOverride = (event, _) => events.add(event);
    ...
    expect(events, contains('masjid_deep_link_opened'));
```

Reset `MixpanelService.instance.trackOverride = null;` in `tearDown`.

- [ ] **Step 2: Run to verify it fails**

Run: `flutter test test/deep_link_service_navigation_test.dart`
Expected: FAIL — event missing

- [ ] **Step 3: Implement**

In `_handleMasjidUri`, after pushing `MasjidDetailsScreen`:

```dart
    MixpanelService.instance.track('masjid_deep_link_opened', {
      'masjid_id': placeId,
      'masjid_name': masjid.displayName,
      'journey_id': currentJourneyId ?? '',
      'share_id': currentShareId ?? '',
      'deep_link_source': 'shared_video_webpage',
      'platform': 'android_app',
    });
```

Add the import.

- [ ] **Step 4: Run tests**

Run: `flutter test test/deep_link_service_navigation_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/services/deep_link_service.dart lib/services/mixpanel_service.dart test/deep_link_service_navigation_test.dart
git commit -m "feat(app): emit masjid_deep_link_opened"
```

---

### Task 15: Pass analytics context into the embed WebView

**Files:**
- Modify: `lib/features/home/widgets/broadcast_video_player.dart`
- Test: `test/broadcast_video_player_test.dart`

**Interfaces:**
- Produces: `withAnalyticsFragment(String url, Map<String, String> values) -> String`.

- [ ] **Step 1: Write the failing test**

```dart
// test/broadcast_video_player_test.dart
test('appends analytics context as a fragment', () {
  final url = withAnalyticsFragment(
    'https://muslim360.in/embed/m1?for_app=1',
    {'v': 'dev1', 'u': 'u1', 'j': 'j1', 's': 's1'},
  );
  expect(url, contains('#'));
  expect(url, contains('v=dev1'));
  expect(url, contains('s=s1'));
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `flutter test test/broadcast_video_player_test.dart`
Expected: FAIL — function undefined

- [ ] **Step 3: Implement**

```dart
// lib/features/home/widgets/broadcast_video_player.dart — top level
String withAnalyticsFragment(String url, Map<String, String> values) {
  final filtered = <String, String>{
    for (final e in values.entries)
      if (e.value.trim().isNotEmpty) e.key: e.value.trim(),
  };
  if (filtered.isEmpty) return url;
  return '$url#${Uri(queryParameters: filtered).query}';
}
```

In `initState`, after building `_embedUrl`:

```dart
    _embedUrl = withAnalyticsFragment(_embedUrl, {
      'v': MixpanelService.instance.visitorId ?? '',
      'u': StoreManager.instance.userId ?? '',
      'j': DeepLinkService.instance.currentJourneyId ?? '',
      's': DeepLinkService.instance.currentShareId ?? '',
    });
```

Add imports.

- [ ] **Step 4: Run tests**

Run: `flutter test test/broadcast_video_player_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lib/features/home/widgets/broadcast_video_player.dart test/broadcast_video_player_test.dart
git commit -m "feat(app): pass analytics context to the embed player"
```

---

## Final verification

- [ ] Backend: `.venv/bin/python3 -m pytest tests -q` → all pass
- [ ] Backend: `node --test tests/js` → all pass
- [ ] App: `flutter analyze` → no errors
- [ ] App: `flutter test` → all pass
- [ ] Manual: create a share from web → open on device → confirm `video_landing_page_viewed`, `video_playback_started`, `click_on_view_masjid_cta`, `masjid_deep_link_opened` in Mixpanel Live View with the same `share_id`/`journey_id`.

## Configuration

`MIXPANEL_TOKEN` is set in `m360-backend/.env`, `m360-flutter-app/.env.dev` and
`.env.prod`. `MIXPANEL_API_HOST` defaults to `https://api.mixpanel.com` (US);
switch it to `https://api-eu.mixpanel.com` if the project is in the EU region.
