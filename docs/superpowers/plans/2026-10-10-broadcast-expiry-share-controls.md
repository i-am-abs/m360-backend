# Broadcast Expiry + Share Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional 30-day auto-delete and an opt-out share control to masjid broadcasts, enforced in both the in-app feed and the server-rendered public share page.

**Architecture:** Two optional fields (`allow_sharing`, `expires_at`) are added to `broadcast_messages` docs. Read paths filter expired posts and the share page renders one of three states (available / expired / unavailable). Pure helper functions in `app/utils/broadcast.py` hold the decision logic so it is unit-testable without MongoDB. Flutter adds two checkboxes to the create screen, sends the flags, and the feed card hides Share + shows an expiry note.

**Tech Stack:** FastAPI + Pydantic + MongoDB (pymongo) backend; Jinja2 templates; Flutter/Dart (Provider, Dio via ApiService); pytest; flutter test.

## Global Constraints

- Expiry is a single fixed value: **30 days** (`DEFAULT_EXPIRY_DAYS = 30`); only `30` is accepted.
- Both controls default **off** on create: `allow_sharing = true`, `expires_at = null`.
- Backend is the source of truth for `expires_at` (never trust client timestamps).
- Legacy docs missing the fields behave as `allow_sharing = true`, `expires_at = null`.
- Share-page precedence: `allow_sharing == false` → unavailable; else expired → expired; else available.
- Both controls apply to all announcement types.
- No hard-delete of Mux assets; no post-hoc editing.
- Flutter: no user-visible hardcoded strings — every string needs an ARB entry (en + hi) and `flutter gen-l10n`.
- Backend test command: `.venv/bin/python -m pytest -q` (run from `m360-backend/`). Flutter test command: `flutter test`.
- Timestamps are ISO-8601 UTC.

---

## File Structure

**Backend (`m360-backend`)**
- Create `app/utils/broadcast.py` — pure helpers: `compute_expires_at`, `is_expired`, `resolve_share_state`.
- Modify `app/schemas/broadcast_feed.py` — add request fields.
- Modify `app/interfaces/broadcast_feed_repository.py` — `create_message` signature.
- Modify `app/repositories/mongo_broadcast_repository.py` — persist fields, add index, filter expired.
- Modify `app/services/broadcast_feed_service.py` — compute + pass expiry.
- Modify `app/web/share.py` — branch on share state.
- Create `app/web/templates/share_unavailable.html`, `app/web/templates/share_expired.html`.
- Create `tests/test_broadcast_expiry.py`, `tests/test_share_state.py`.

**Flutter (`m360-flutter-app`)**
- Modify `lib/services/api_services/broadcast_service.dart` — model + `postMessage`.
- Modify `lib/features/home/screens/broadcast/create_broadcast.dart` — checkboxes.
- Modify `lib/features/home/widgets/broadcast_message_card.dart` — hide share + note.
- Modify `lib/features/home/screens/broadcast/broadcast_feed.dart` — pass flags + short-circuit share.
- Modify `lib/l10n/app_en.arb`, `lib/l10n/app_hi.arb`.
- Create `test/broadcast_expiry_test.dart`.

---

## Task 1: Backend pure helpers (`app/utils/broadcast.py`)

**Files:**
- Create: `app/utils/broadcast.py`
- Test: `tests/test_share_state.py`

**Interfaces:**
- Produces:
  - `DEFAULT_EXPIRY_DAYS: int = 30`
  - `compute_expires_at(expires_in_days: Optional[int], now: Optional[datetime] = None) -> Optional[str]`
  - `is_expired(expires_at: Optional[str], now: Optional[datetime] = None) -> bool`
  - `resolve_share_state(message: dict, now: Optional[datetime] = None) -> str` (`"available" | "expired" | "unavailable"`)

- [ ] **Step 1: Write the failing test** — `tests/test_share_state.py`

```python
from datetime import datetime, timedelta, timezone

from app.utils.broadcast import (
    compute_expires_at,
    is_expired,
    resolve_share_state,
)

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_compute_expires_at_none_when_no_days():
    assert compute_expires_at(None, now=NOW) is None


def test_compute_expires_at_adds_30_days():
    assert compute_expires_at(30, now=NOW) == (NOW + timedelta(days=30)).isoformat()


def test_is_expired_false_for_none():
    assert is_expired(None, now=NOW) is False


def test_is_expired_false_for_future():
    future = (NOW + timedelta(days=1)).isoformat()
    assert is_expired(future, now=NOW) is False


def test_is_expired_true_for_past():
    past = (NOW - timedelta(days=1)).isoformat()
    assert is_expired(past, now=NOW) is True


def test_resolve_available_default():
    assert resolve_share_state({}, now=NOW) == "available"


def test_resolve_unavailable_when_sharing_disabled():
    assert resolve_share_state({"allow_sharing": False}, now=NOW) == "unavailable"


def test_resolve_unavailable_beats_expired():
    msg = {"allow_sharing": False, "expires_at": (NOW - timedelta(days=1)).isoformat()}
    assert resolve_share_state(msg, now=NOW) == "unavailable"


def test_resolve_expired_when_past():
    msg = {"expires_at": (NOW - timedelta(days=1)).isoformat()}
    assert resolve_share_state(msg, now=NOW) == "expired"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_share_state.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.utils.broadcast'`

- [ ] **Step 3: Write minimal implementation** — `app/utils/broadcast.py`

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

DEFAULT_EXPIRY_DAYS = 30
ALLOWED_EXPIRY_DAYS = {DEFAULT_EXPIRY_DAYS}


def compute_expires_at(
    expires_in_days: Optional[int],
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Return an ISO-8601 UTC expiry, or None when the post never expires."""
    if expires_in_days is None:
        return None
    days = expires_in_days if expires_in_days in ALLOWED_EXPIRY_DAYS else DEFAULT_EXPIRY_DAYS
    base = now or datetime.now(timezone.utc)
    return (base + timedelta(days=days)).isoformat()


def is_expired(expires_at: Optional[str], now: Optional[datetime] = None) -> bool:
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= (now or datetime.now(timezone.utc))


def resolve_share_state(message: dict, now: Optional[datetime] = None) -> str:
    """Which share page to render. 'unavailable' takes precedence over 'expired'."""
    if message.get("allow_sharing", True) is False:
        return "unavailable"
    if is_expired(message.get("expires_at"), now):
        return "expired"
    return "available"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_share_state.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/broadcast.py tests/test_share_state.py
git commit -m "feat(broadcast): add expiry + share-state helpers"
```

---

## Task 2: Persist `allow_sharing` + `expires_at` on create

**Files:**
- Modify: `app/schemas/broadcast_feed.py`
- Modify: `app/interfaces/broadcast_feed_repository.py`
- Modify: `app/repositories/mongo_broadcast_repository.py`
- Modify: `app/services/broadcast_feed_service.py`
- Test: `tests/test_broadcast_expiry.py`

**Interfaces:**
- Consumes: `compute_expires_at` from Task 1.
- Produces: `create_message(masjid_id, sender, msg_type, text, video_url, campaign_id, thumbnail_url=None, mux_asset_id=None, mux_upload_id=None, allow_sharing=True, expires_at=None) -> dict`; created docs carry `allow_sharing: bool` and `expires_at: str | None`.

- [ ] **Step 1: Extend the request schema** — `app/schemas/broadcast_feed.py`

```python
class BroadcastMessageCreate(BaseModel):
    message_type: str = "text"
    text: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    mux_asset_id: Optional[str] = None
    mux_upload_id: Optional[str] = None
    campaign_id: Optional[str] = None
    allow_sharing: bool = True
    expires_in_days: Optional[int] = None
```

- [ ] **Step 2: Write the failing test** — `tests/test_broadcast_expiry.py`

```python
from datetime import datetime, timedelta, timezone

from app.repositories.mongo_broadcast_repository import MongoBroadcastFeedRepository


class _FakeCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []

    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    def insert_one(self, doc):
        self.docs.append(dict(doc))

        class _R:
            inserted_id = "fake-id"

        return _R()


class _FakeDb:
    def __init__(self):
        self.col = _FakeCollection()

    def __getitem__(self, name):
        return self.col


def _repo():
    return MongoBroadcastFeedRepository(_FakeDb())


def test_create_message_defaults_sharing_true_no_expiry():
    repo = _repo()
    msg = repo.create_message(
        masjid_id="m1", sender={"user_id": "u1"}, msg_type="video",
        text="hi", video_url="v", campaign_id=None,
    )
    assert msg["allow_sharing"] is True
    assert msg["expires_at"] is None


def test_create_message_persists_expiry_and_disabled_sharing():
    repo = _repo()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    msg = repo.create_message(
        masjid_id="m1", sender={"user_id": "u1"}, msg_type="video",
        text="hi", video_url="v", campaign_id=None,
        allow_sharing=False, expires_at=expires,
    )
    assert msg["allow_sharing"] is False
    assert msg["expires_at"] == expires
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_broadcast_expiry.py -q`
Expected: FAIL with `TypeError: create_message() got an unexpected keyword argument 'allow_sharing'`

- [ ] **Step 4: Update the interface** — `app/interfaces/broadcast_feed_repository.py`

Add to `create_message` signature (after `mux_upload_id`):

```python
            mux_upload_id: Optional[str] = None,
            allow_sharing: bool = True,
            expires_at: Optional[str] = None,
    ) -> dict:
```

- [ ] **Step 5: Update the Mongo repo** — `app/repositories/mongo_broadcast_repository.py`

In `create_message` add the two params and persist them; add the sparse index in `_ensure_indexes`:

```python
    def _ensure_indexes(self) -> None:
        self._messages.create_index([("masjid_id", 1), ("created_at", -1)])
        self._messages.create_index([("masjid_id", 1), ("updated_at", -1)])
        self._messages.create_index([("sender.user_id", 1)])
        self._messages.create_index([("expires_at", 1)], sparse=True)

    def create_message(
            self,
            masjid_id: str,
            sender: dict,
            msg_type: str,
            text: Optional[str],
            video_url: Optional[str],
            campaign_id: Optional[str],
            thumbnail_url: Optional[str] = None,
            mux_asset_id: Optional[str] = None,
            mux_upload_id: Optional[str] = None,
            allow_sharing: bool = True,
            expires_at: Optional[str] = None,
    ) -> dict:
        now_iso = self._now_iso()
        doc: Dict[str, Any] = {
            "masjid_id": masjid_id,
            "sender": {
                "user_id": sender["user_id"],
                "name": sender.get("name", ""),
                "role": sender.get("role", ""),
                "avatar_url": sender.get("avatar_url"),
            },
            "message_type": msg_type,
            "text": text,
            "video_url": video_url,
            "campaign_id": campaign_id,
            "thumbnail_url": thumbnail_url,
            "mux_asset_id": mux_asset_id,
            "mux_upload_id": mux_upload_id,
            "mux_playback_id": None,
            "allow_sharing": allow_sharing,
            "expires_at": expires_at,
            "comments": [],
            "reactions": {emoji: [] for emoji in ALLOWED_EMOJIS},
            "reaction_counts": {emoji: 0 for emoji in ALLOWED_EMOJIS},
            "view_count": 0,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        result = self._messages.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._as_dict(doc)
```

- [ ] **Step 6: Update the service** — `app/services/broadcast_feed_service.py`

```python
from app.utils.broadcast import compute_expires_at
```
In `post_message`, compute and pass:

```python
        expires_at = compute_expires_at(data.get("expires_in_days"))
        message = self._broadcast_repo.create_message(
            masjid_id=masjid_id,
            sender=sender_info,
            msg_type=data.get("message_type", "text"),
            text=data.get("text"),
            video_url=data.get("video_url"),
            thumbnail_url=data.get("thumbnail_url"),
            mux_asset_id=data.get("mux_asset_id"),
            mux_upload_id=data.get("mux_upload_id"),
            campaign_id=data.get("campaign_id"),
            allow_sharing=bool(data.get("allow_sharing", True)),
            expires_at=expires_at,
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_broadcast_expiry.py -q`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add app/schemas/broadcast_feed.py app/interfaces/broadcast_feed_repository.py app/repositories/mongo_broadcast_repository.py app/services/broadcast_feed_service.py tests/test_broadcast_expiry.py
git commit -m "feat(broadcast): persist allow_sharing and expires_at on create"
```

---

## Task 3: Exclude expired posts from the feed

**Files:**
- Modify: `app/repositories/mongo_broadcast_repository.py` (`get_messages`)

**Interfaces:**
- Consumes: `is_expired`/`resolve_share_state` (Task 1); fields (Task 2).
- Produces: `get_messages` never returns expired docs across initial, `before`, and `since` paths.

- [ ] **Step 1: Update `get_messages`** — `app/repositories/mongo_broadcast_repository.py`

Replace the query-building block with an `$and` that always includes the expiry filter (keeps `$or` usage from clobbering):

```python
    def get_messages(
            self,
            masjid_id: str,
            cursor: Optional[datetime],
            since: Optional[datetime],
            limit: int,
            user_id: Optional[str] = None,
    ) -> dict:
        now_iso = self._now_iso()
        not_expired = {
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$exists": False}},
                {"expires_at": {"$gt": now_iso}},
            ]
        }
        conditions: List[Dict[str, Any]] = [{"masjid_id": masjid_id}, not_expired]
        if cursor:
            conditions.append({"created_at": {"$lt": cursor.isoformat()}})
        if since:
            conditions.append({"updated_at": {"$gt": since.isoformat()}})
        query: Dict[str, Any] = {"$and": conditions}

        docs = (
            list(self._messages.find(query).sort("created_at", -1).limit(limit))
        )

        has_more = len(docs) >= limit
        next_cursor = None
        if has_more and docs:
            next_cursor = docs[-1].get("created_at")

        messages = []
        for doc in docs:
            msg = self._as_dict(doc)
            if user_id:
                reactions = doc.get("reactions", {})
                msg["my_reaction"] = next(
                    (e for e, users in reactions.items() if user_id in users),
                    None,
                )
            messages.append(msg)

        return {
            "messages": messages,
            "pagination": {"has_more": has_more, "next_cursor": next_cursor},
        }
```

Ensure `from typing import Any, Dict, List, Optional` is imported at the top of the file.

- [ ] **Step 2: Manual verification (no DB needed)**

Run: `.venv/bin/python -c "import ast; ast.parse(open('app/repositories/mongo_broadcast_repository.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Run the full backend suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add app/repositories/mongo_broadcast_repository.py
git commit -m "feat(broadcast): hide expired posts from the feed"
```

---

## Task 4: Share page renders expired / unavailable states

**Files:**
- Create: `app/web/templates/share_unavailable.html`
- Create: `app/web/templates/share_expired.html`
- Modify: `app/web/share.py`
- Test: `tests/test_share_state.py` (already covers resolution); add a template-render smoke test.

**Interfaces:**
- Consumes: `resolve_share_state` (Task 1).
- Produces: `GET /s/{id}` returns the correct template per state.

- [ ] **Step 1: Create `app/web/templates/share_unavailable.html`**

```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not available to share | Muslim 360</title>
<style>
  body{margin:0;font-family:-apple-system,"Plus Jakarta Sans",system-ui,sans-serif;
    background:#F8F9FA;color:#091914;display:flex;min-height:100vh;
    align-items:center;justify-content:center;text-align:center;padding:24px}
  .cta{display:inline-block;margin:6px;background:linear-gradient(#61D47D,#ADFF8D);
    color:#091914;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:12px}
</style></head><body><div>
  <h1>This content isn't available to share</h1>
  <p>The masjid has turned off sharing for this announcement.</p>
  <a class="cta" href="{{ app_store_url }}">Get it on the App Store</a>
  <a class="cta" href="{{ play_store_url }}">Get it on Google Play</a>
</div></body></html>
```

- [ ] **Step 2: Create `app/web/templates/share_expired.html`**

```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Post expired | Muslim 360</title>
<style>
  body{margin:0;font-family:-apple-system,"Plus Jakarta Sans",system-ui,sans-serif;
    background:#F8F9FA;color:#091914;display:flex;min-height:100vh;
    align-items:center;justify-content:center;text-align:center;padding:24px}
  .cta{display:inline-block;margin:6px;background:linear-gradient(#61D47D,#ADFF8D);
    color:#091914;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:12px}
</style></head><body><div>
  <h1>This post has expired</h1>
  <p>Open the app to see the latest announcements from this masjid.</p>
  <a class="cta" href="{{ app_store_url }}">Get it on the App Store</a>
  <a class="cta" href="{{ play_store_url }}">Get it on Google Play</a>
</div></body></html>
```

- [ ] **Step 3: Branch in `app/web/share.py`**

Add import and gate before the normal render:

```python
from app.utils.broadcast import resolve_share_state
```
After `ctx = build_share_context(message, masjid, settings)`, replace the final render with:

```python
    state = resolve_share_state(message)
    if state in {"unavailable", "expired"}:
        template = (
            "share_unavailable.html" if state == "unavailable" else "share_expired.html"
        )
        html = env.get_template(template).render(
            marketing_site_url=settings.marketing_site_url,
            play_store_url=settings.play_store_url,
            app_store_url=settings.app_store_url,
        )
        return HTMLResponse(html)
    html = env.get_template("share.html").render(**ctx)
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
```

- [ ] **Step 4: Add a render smoke test** — append to `tests/test_share_state.py`

```python
def test_templates_render_with_context():
    from app.web.templating import env

    for name in ("share_unavailable.html", "share_expired.html"):
        html = env.get_template(name).render(
            marketing_site_url="https://m360.app",
            play_store_url="https://play.google.com/x",
            app_store_url="https://apps.apple.com/x",
        )
        assert "Get it on Google Play" in html
        assert "Get it on the App Store" in html
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_share_state.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/web/templates/share_unavailable.html app/web/templates/share_expired.html app/web/share.py tests/test_share_state.py
git commit -m "feat(share): render expired and unavailable share pages"
```

---

## Task 5: Flutter model + service (`broadcast_service.dart`)

**Files:**
- Modify: `lib/services/api_services/broadcast_service.dart`

**Interfaces:**
- Produces: `BroadcastMessage.allowSharing: bool`, `BroadcastMessage.expiresAt: DateTime?`; `postMessage(..., bool allowSharing = true, int? expiresInDays)` sending `allow_sharing` + `expires_in_days`.

- [ ] **Step 1: Add fields to `BroadcastMessage`**

Add to the class fields/constructor and `fromJson`/`toJson`:

```dart
  final bool allowSharing;
  final DateTime? expiresAt;
```
Constructor: `this.allowSharing = true, this.expiresAt,`
`fromJson`:
```dart
      allowSharing: json['allow_sharing'] as bool? ?? true,
      expiresAt: (json['expires_at'] as String?)?.isNotEmpty == true
          ? DateTime.tryParse(json['expires_at'] as String)
          : null,
```
`toJson`:
```dart
    'allow_sharing': allowSharing,
    if (expiresAt != null) 'expires_at': expiresAt!.toIso8601String(),
```

- [ ] **Step 2: Extend `postMessage`**

```dart
  Future<BroadcastMessage> postMessage(
    String masjidId, String text, {
    String? videoUrl,
    String? thumbnailUrl,
    String? campaignId,
    String? muxAssetId,
    String? muxUploadId,
    bool allowSharing = true,
    int? expiresInDays,
  }) async {
```
Add to the request body map:
```dart
        'allow_sharing': allowSharing,
        if (expiresInDays != null) 'expires_in_days': expiresInDays,
```

- [ ] **Step 3: Analyze**

Run: `flutter analyze lib/services/api_services/broadcast_service.dart`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add lib/services/api_services/broadcast_service.dart
git commit -m "feat(broadcast): model + send allow_sharing and expiry"
```

---

## Task 6: Create screen checkboxes

**Files:**
- Modify: `lib/features/home/screens/broadcast/create_broadcast.dart`

**Interfaces:**
- Consumes: `postMessage(..., allowSharing:, expiresInDays:)` (Task 5).

- [ ] **Step 1: Add state**

```dart
  bool _allowSharing = true;   // unchecked "do not allow sharing" => sharing allowed
  bool _autoDelete = false;    // unchecked => no expiry
```

- [ ] **Step 2: Add two checkboxes in `_buildVideoPreviewWithForm`, after the caption field**

Insert before the existing disclaimer container a widget with two rows:

```dart
          Container(
            decoration: BoxDecoration(
              color: const Color(0xFFF8F9FA),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFCBD0D6).withValues(alpha: 0.3)),
            ),
            child: Column(
              children: [
                _buildToggleRow(
                  value: !_allowSharing,
                  label: l10n?.broadcast_share_disabled_label ??
                      'Do not allow sharing this video outside the app.',
                  onChanged: (v) => setState(() => _allowSharing = !v),
                ),
                const Divider(height: 1),
                _buildToggleRow(
                  value: _autoDelete,
                  label: l10n?.broadcast_auto_delete_label ??
                      'Auto-delete video after 1 month.',
                  onChanged: (v) => setState(() => _autoDelete = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
```

Add the helper:

```dart
  Widget _buildToggleRow({
    required bool value,
    required String label,
    required ValueChanged<bool> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          Checkbox(
            value: value,
            onChanged: _isUploading ? null : (v) => onChanged(v ?? false),
            activeColor: const Color(0xFF45D07C),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
          ),
          Expanded(
            child: GestureDetector(
              onTap: _isUploading ? null : () => onChanged(!value),
              child: Text(
                label,
                style: const TextStyle(
                  fontSize: 13,
                  fontFamily: 'PlusJakartaSans',
                  color: Color(0xFF5D6C67),
                  height: 1.4,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
```

- [ ] **Step 3: Send the flags on submit**

In `_postAnnouncement`, update the `postMessage` call:

```dart
      await BroadcastService.instance.postMessage(
        widget.masjidId,
        _captionController.text.trim(),
        muxAssetId: mux.assetId,
        muxUploadId: mux.uploadId,
        allowSharing: _allowSharing,
        expiresInDays: _autoDelete ? 30 : null,
      );
```

- [ ] **Step 4: Analyze**

Run: `flutter analyze lib/features/home/screens/broadcast/create_broadcast.dart`
Expected: no new errors

- [ ] **Step 5: Commit**

```bash
git add lib/features/home/screens/broadcast/create_broadcast.dart
git commit -m "feat(broadcast): add share + auto-delete toggles to create screen"
```

---

## Task 7: Feed card + feed honour the flags

**Files:**
- Modify: `lib/features/home/widgets/broadcast_message_card.dart`
- Modify: `lib/features/home/screens/broadcast/broadcast_feed.dart`

**Interfaces:**
- Consumes: `BroadcastMessage.allowSharing`, `BroadcastMessage.expiresAt` (Task 5).

- [ ] **Step 1: Card — hide Share when disabled**

In `broadcast_message_card.dart`, wrap the Share `Padding(...)` (line ~310) in a conditional using a new param. Add a widget field `final bool allowSharing;` (default `true`) with constructor `this.allowSharing = true,`, and:

```dart
          if (widget.allowSharing)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: InkWell(
                onTap: widget.onShare ?? () => _share(context),
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCBD0D6).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(Icons.ios_share, size: 18, color: Color(0xFF5D6C67)),
                ),
              ),
            ),
```

- [ ] **Step 2: Card — show the expiry note**

In the card content (below the views/time row, before reactions), add:

```dart
        if (widget.expiresAt != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(
              children: [
                const Icon(Icons.schedule, size: 14, color: Color(0xFF5D6C67)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    AppLocalizations.of(context)?.broadcast_expiry_note ??
                        'This will be automatically removed in 30 days.',
                    style: const TextStyle(
                      fontSize: 12,
                      fontFamily: 'PlusJakartaSans',
                      color: Color(0xFF5D6C67),
                    ),
                  ),
                ),
              ],
            ),
          ),
```
Add widget field `final DateTime? expiresAt;` with `this.expiresAt,`.

- [ ] **Step 3: Feed — pass flags through**

In `broadcast_feed.dart` where `BroadcastMessageCard(...)` is constructed (~line 420), pass:
```dart
      allowSharing: msg.allowSharing,
      expiresAt: msg.expiresAt,
```
And short-circuit `_shareMessage`:
```dart
  void _shareMessage(BroadcastMessage msg) {
    if (!msg.allowSharing) return;
    ...
  }
```

- [ ] **Step 4: Analyze**

Run: `flutter analyze lib/features/home/widgets/broadcast_message_card.dart lib/features/home/screens/broadcast/broadcast_feed.dart`
Expected: no new errors

- [ ] **Step 5: Commit**

```bash
git add lib/features/home/widgets/broadcast_message_card.dart lib/features/home/screens/broadcast/broadcast_feed.dart
git commit -m "feat(broadcast): hide share and show expiry note per post"
```

---

## Task 8: Localization (en + hi)

**Files:**
- Modify: `lib/l10n/app_en.arb`, `lib/l10n/app_hi.arb`

- [ ] **Step 1: Add keys to `app_en.arb`**

```json
  "broadcast_share_disabled_label": "Do not allow sharing this video outside the app.",
  "broadcast_auto_delete_label": "Auto-delete video after 1 month.",
  "broadcast_expiry_note": "This will be automatically removed in 30 days.",
```

- [ ] **Step 2: Add Hindi keys to `app_hi.arb`**

```json
  "broadcast_share_disabled_label": "इस वीडियो को ऐप के बाहर साझा करने की अनुमति न दें।",
  "broadcast_auto_delete_label": "1 महीने बाद वीडियो स्वतः हटा दें।",
  "broadcast_expiry_note": "यह 30 दिनों में स्वतः हटा दिया जाएगा।",
```

- [ ] **Step 3: Generate localizations**

Run: `flutter gen-l10n`
Expected: completes without error

- [ ] **Step 4: Analyze**

Run: `flutter analyze`
Expected: no new errors

- [ ] **Step 5: Commit**

```bash
git add lib/l10n/app_en.arb lib/l10n/app_hi.arb lib/l10n/app_localizations*.dart
git commit -m "feat(broadcast): localize share + expiry labels"
```

---

## Task 9: Flutter widget tests

**Files:**
- Create: `test/broadcast_expiry_test.dart`

- [ ] **Step 1: Write the test** — `test/broadcast_expiry_test.dart`

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:m360/services/api_services/broadcast_service.dart';

void main() {
  test('BroadcastMessage defaults allowSharing true and no expiry', () {
    final m = BroadcastMessage.fromJson({
      'id': 'm1',
      'message_type': 'video',
      'sender': {'user_id': 'u1'},
      'created_at': '2026-10-10T00:00:00Z',
    });
    expect(m.allowSharing, isTrue);
    expect(m.expiresAt, isNull);
  });

  test('BroadcastMessage parses allow_sharing=false and expires_at', () {
    final m = BroadcastMessage.fromJson({
      'id': 'm1',
      'message_type': 'video',
      'sender': {'user_id': 'u1'},
      'created_at': '2026-10-10T00:00:00Z',
      'allow_sharing': false,
      'expires_at': '2026-11-09T00:00:00Z',
    });
    expect(m.allowSharing, isFalse);
    expect(m.expiresAt, isNotNull);
  });
}
```

- [ ] **Step 2: Run the test**

Run: `flutter test test/broadcast_expiry_test.dart`
Expected: PASS (2 passed)

- [ ] **Step 3: Run the full Flutter suite**

Run: `flutter test`
Expected: PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add test/broadcast_expiry_test.dart
git commit -m "test(broadcast): cover allow_sharing + expires_at parsing"
```

---

## Verification Checklist (run before PR)

- [ ] Backend: `.venv/bin/python -m pytest -q` → all pass.
- [ ] Flutter: `flutter analyze` → no new issues; `flutter test` → all pass.
- [ ] Create a broadcast with auto-delete on → doc has `expires_at = created_at + 30d`.
- [ ] Feed hides a post once `expires_at` passes (set a past timestamp manually to confirm).
- [ ] `/s/{id}` renders expired page for an expired post and unavailable page for `allow_sharing=false`.
- [ ] Legacy post (no fields) still shows a normal share page and appears in the feed.
