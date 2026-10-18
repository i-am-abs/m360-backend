# Share Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the server-rendered `/s/{id}` share page to the new portrait design, and make "Follow Masjid" open the app deep link with a Play Store / App Store fallback.

**Architecture:** Two backend changes only: extend `build_share_context` with sender fields, then rewrite `app/web/templates/share.html` (header, full-bleed media, footer CTAs). The existing HLS player script and the expired/unavailable gates are preserved.

**Tech Stack:** FastAPI + Jinja2 templates, vanilla CSS/JS, pytest.

## Global Constraints

- `/s/{id}` gating (expired → `share_expired.html`, sharing-disabled → `share_unavailable.html`) must not change.
- "Follow Masjid" behavior: Android `intent://…` with `browser_fallback_url=<play_store_url>`; iOS navigate to the deep link then redirect to `app_store_url` if still visible after ~1.2s; desktop → `play_store_url`. No server-side install detection.
- "Share" = `navigator.share` else clipboard copy (existing toast behavior).
- WhatsApp button = `https://wa.me/?text=<encoded caption + page URL>`.
- Sender fallbacks: missing name/role → "Admin"; missing avatar → masjid avatar.
- No new backend endpoints; no Flutter changes.
- Do not push. (Controller will ask which branch before any push.)
- Backend test command: `.venv/bin/python -m pytest -q` (from `m360-backend/`).

---

## File Structure

- Modify: `app/web/share_context.py` — add `sender_name`, `sender_role`, `sender_avatar_url`.
- Create: `tests/test_share_context.py` — sender-field tests.
- Modify: `app/web/templates/share.html` — full layout redesign + CTA JS.
- Create: `tests/test_share_template.py` — render smoke test.

---

## Task 1: Sender fields in the share context

**Files:**
- Modify: `app/web/share_context.py`
- Test: `tests/test_share_context.py`

**Interfaces:**
- Produces: `build_share_context(...)` return dict gains `sender_name: str`, `sender_role: str`, `sender_avatar_url: str`.

- [ ] **Step 1: Write the failing test** — `tests/test_share_context.py`

```python
from app.core.config import Settings
from app.web.share_context import build_share_context


def _settings() -> Settings:
    return Settings(
        share_web_base_url="https://m360.vyapari.link",
        android_package_name="com.starkinnovations.m360",
    )


def _masjid() -> dict:
    return {
        "name": "Masjid Al Noor",
        "city": "Thane",
        "state": "Maharashtra",
        "photo_url": "https://img/masjid.jpg",
        "management": {"is_claimed": True},
    }


def test_sender_fields_from_message():
    msg = {
        "id": "m1",
        "text": "Salaam",
        "created_at": "2026-10-13T10:00:00+00:00",
        "sender": {"user_id": "u1", "name": "Najim Ahmed", "role": "Imam",
                   "avatar_url": "https://img/u1.jpg"},
    }
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_name"] == "Najim Ahmed"
    assert ctx["sender_role"] == "Imam"
    assert ctx["sender_avatar_url"] == "https://img/u1.jpg"


def test_sender_fallbacks_when_missing():
    msg = {"id": "m2", "text": "Salaam", "created_at": "2026-10-13T10:00:00+00:00"}
    ctx = build_share_context(msg, _masjid(), _settings())
    assert ctx["sender_name"] == "Admin"
    assert ctx["sender_role"] == "Admin"
    assert ctx["sender_avatar_url"] == "https://img/masjid.jpg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_share_context.py -q`
Expected: FAIL with `KeyError: 'sender_name'`

- [ ] **Step 3: Implement** — in `app/web/share_context.py`, inside `build_share_context`, before `return {`, add:

```python
    sender = message.get("sender") or {}
    sender_name = (str(sender.get("name") or "").strip()) or "Admin"
    sender_role = (str(sender.get("role") or "").strip()) or "Admin"
    sender_avatar = sender.get("avatar_url") or masjid.get("photo_url") or (
        f"{settings.share_web_base_url}/share-static/masjid-default.png"
    )
```

Then add to the returned dict:

```python
        "sender_name": sender_name,
        "sender_role": sender_role,
        "sender_avatar_url": sender_avatar,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_share_context.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/web/share_context.py tests/test_share_context.py
git commit -m "feat(share): expose sender name/role/avatar in share context"
```

---

## Task 2: Redesign the share template

**Files:**
- Modify: `app/web/templates/share.html`
- Test: `tests/test_share_template.py`

**Interfaces:**
- Consumes: context fields from Task 1 plus existing fields (`masjid_name`, `masjid_location`, `masjid_verified`, `masjid_avatar_url`, `is_video`, `video_hls_url`, `poster_url`, `og_*`, `page_title`, `relative_time`, `canonical_url`, `deep_link_path`, `share_host`, `play_store_url`, `app_store_url`, `android_package`).

- [ ] **Step 1: Replace the page body/stylesheet** in `app/web/templates/share.html` with the new layout. Keep the `<head>` OG/twitter tags as-is. Use this structure (CSS may be adapted but must produce the described layout):

```html
<body>
<div class="page">
  <header class="mhead">
    <img class="mavatar" src="{{ masjid_avatar_url }}" alt="">
    <div class="mmeta">
      <div class="mname">{{ masjid_name }}
        {% if masjid_verified %}<svg class="vbadge" viewBox="0 0 24 24"><path d="M12 2l2.4 2.1 3.1-.5.9 3 2.9 1.3-1.3 2.9 1.3 2.9-2.9 1.3-.9 3-3.1-.5L12 22l-2.4-2.1-3.1.5-.9-3-2.9-1.3 1.3-2.9L1.7 8l2.9-1.3.9-3 3.1.5z"/><path d="M10.6 14.6l-2.2-2.2-1.4 1.4 3.6 3.6 6-6-1.4-1.4z" fill="#fff"/></svg>{% endif %}
      </div>
      <div class="mloc">{{ masjid_location }}</div>
    </div>
    <button class="wa" id="waBtn" aria-label="Share on WhatsApp">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M20.5 3.5A11.8 11.8 0 0 0 12 0C5.4 0 .1 5.3.1 11.9c0 2.1.6 4.2 1.6 6L0 24l6.3-1.6c1.7.9 3.7 1.4 5.7 1.4 6.6 0 11.9-5.3 11.9-11.9 0-3.2-1.2-6.2-3.4-8.4zM12 21.4c-1.8 0-3.5-.5-5-1.4l-.4-.2-3.7.9.9-3.6-.2-.4a9.5 9.5 0 0 1-1.5-5.1c0-5.3 4.3-9.6 9.6-9.6 2.6 0 5 1 6.8 2.8a9.5 9.5 0 0 1 2.8 6.8c0 5.3-4.3 9.6-9.3 9.6zm5.3-7.2c-.3-.1-1.7-.8-2-.9-.3-.1-.5-.1-.7.1-.2.3-.7.9-.9 1.1-.2.2-.3.2-.6.1-.3-.2-1.2-.4-2.2-1.4a8.3 8.3 0 0 1-1.5-1.9c-.2-.3 0-.5.1-.6l.5-.6c.1-.2.2-.3.3-.5.1-.2 0-.4 0-.5 0-.1-.7-1.6-.9-2.2-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2 3.1 4.9 4.3.7.3 1.2.5 1.6.6.7.2 1.3.2 1.8.1.5-.1 1.7-.7 1.9-1.4.2-.7.2-1.2.2-1.4-.1-.2-.3-.3-.6-.4z"/></svg>
    </button>
  </header>

  <main class="media" id="media">
    {% if poster_url %}<img class="poster" src="{{ poster_url }}" alt="">{% else %}<div class="poster placeholder"></div>{% endif %}
    {% if is_video %}
      <button class="playbtn" id="play" aria-label="Play"></button>
      <video id="v" playsinline preload="none" {% if poster_url %}poster="{{ poster_url }}"{% endif %} hidden></video>
    {% endif %}
  </main>

  <footer class="foot">
    <div class="srow">
      <img class="savatar" src="{{ sender_avatar_url }}" alt="">
      <div class="smeta">
        <div class="srole">{{ sender_role }}
          {% if masjid_verified %}<svg class="vbadge" viewBox="0 0 24 24"><path d="M12 2l2.4 2.1 3.1-.5.9 3 2.9 1.3-1.3 2.9 1.3 2.9-2.9 1.3-.9 3-3.1-.5L12 22l-2.4-2.1-3.1.5-.9-3-2.9-1.3 1.3-2.9L1.7 8l2.9-1.3.9-3 3.1.5z"/><path d="M10.6 14.6l-2.2-2.2-1.4 1.4 3.6 3.6 6-6-1.4-1.4z" fill="#fff"/></svg>{% endif %}
        </div>
        <div class="sname">{{ sender_name }}</div>
      </div>
      <div class="stime">{{ relative_time }}</div>
    </div>
    <div class="ctas">
      <button class="primary" id="followBtn">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#091914" stroke-width="2"><path d="M15 19a6 6 0 0 0-12 0"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>
        Follow Masjid
      </button>
      <button class="ghost" id="shareBtn">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#0B7C43" stroke-width="2"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M12 15V3"/><path d="M8 7l4-4 4 4"/></svg>
        Share
      </button>
    </div>
  </footer>
</div>
<div class="toast" id="toast">Link copied</div>
```

CSS essentials: `.page{height:100dvh;display:flex;flex-direction:column;background:#fff}`; header fixed height with avatar/name; `.media{flex:1;min-height:0;position:relative;background:#000;overflow:hidden}`, `.poster{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}`, `.playbtn` centered circular overlay; `.foot{padding:14px 16px 18px;border-radius:18px 18px 0 0;margin-top:-18px;background:#fff;position:relative;z-index:2}`, `.ctas{display:flex;gap:10px;margin-top:12px}` with `.primary{flex:1;background:linear-gradient(#61D47D,#ADFF8D)}` and `.ghost{flex:1;border:1px solid #45D07C;color:#0B7C43}`. Badge `.vbadge{width:14px;height:14px;fill:#2D9CDB}`.

- [ ] **Step 2: Add the CTA script** (replace the old `openApp`/`sharePage`/`openApp` logic with this, keeping the existing HLS player script):

```html
<script>
  var SHARE_HOST = {{ share_host | tojson }};
  var DEEP_PATH = {{ deep_link_path | tojson }};
  var PLAY_URL = {{ play_store_url | tojson }};
  var APPSTORE_URL = {{ app_store_url | tojson }};
  var ANDROID_PKG = {{ android_package | tojson }};
  var HLS_URL = {{ (video_hls_url or "") | tojson }};
  var PAGE_URL = {{ canonical_url | tojson }};
  var WA_TEXT = {{ (og_description ~ " " ~ canonical_url) | tojson }};

  var UA = navigator.userAgent || "";
  var IS_ANDROID = /android/i.test(UA);
  var IS_IOS = /iphone|ipad|ipod/i.test(UA) || (/Macintosh/.test(UA) && navigator.maxTouchPoints > 1);

  function openApp() {
    if (IS_ANDROID) {
      var start = Date.now();
      setTimeout(function () {
        if (Date.now() - start < 2000 && !document.hidden) window.location = PLAY_URL;
      }, 1100);
      window.location = "intent://" + SHARE_HOST + DEEP_PATH +
        "#Intent;scheme=https;package=" + ANDROID_PKG +
        ";S.browser_fallback_url=" + encodeURIComponent(PLAY_URL) + ";end";
      return;
    }
    if (IS_IOS) {
      var fallback = setTimeout(function () { window.location = APPSTORE_URL; }, 1200);
      var cancel = function () { clearTimeout(fallback); };
      window.addEventListener("pagehide", cancel, { once: true });
      document.addEventListener("visibilitychange", function () { if (document.hidden) cancel(); });
      window.location = "https://" + SHARE_HOST + DEEP_PATH;
      return;
    }
    window.location = PLAY_URL;
  }

  function sharePage() {
    if (navigator.share) {
      navigator.share({ title: document.title, url: PAGE_URL }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(PAGE_URL).then(function () {
        var t = document.getElementById("toast");
        t.classList.add("show");
        setTimeout(function () { t.classList.remove("show"); }, 1600);
      });
    }
  }

  document.getElementById("followBtn").addEventListener("click", openApp);
  document.getElementById("shareBtn").addEventListener("click", sharePage);
  document.getElementById("waBtn").addEventListener("click", function () {
    window.open("https://wa.me/?text=" + encodeURIComponent(WA_TEXT), "_blank");
  });
</script>
```

Keep the existing HLS play-button script (`hasMSE`, `HLS_URL`, `#play` handling) from the current `share.html`; if it conflicts with the new `#v` element, merge them so clicking `#play` reveals `#v`, sets `src = HLS_URL`, and plays.

- [ ] **Step 3: Write the render smoke test** — `tests/test_share_template.py`

```python
from app.web.templating import env


def _render():
    return env.get_template("share.html").render(
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
        canonical_url="https://m360.vyapari.link/s/m1",
        deep_link_path="/s/m1",
        share_host="m360.vyapari.link",
        play_store_url="https://play.google.com/x",
        app_store_url="https://apps.apple.com/x",
        android_package="com.starkinnovations.m360",
        marketing_site_url="https://muslim360.app",
    )


def test_share_template_renders_new_layout():
    html = _render()
    assert "Masjid Al Noor" in html
    assert "Najim Ahmed" in html
    assert "Imam" in html
    assert "Follow Masjid" in html
    assert 'id="waBtn"' in html
    assert 'id="followBtn"' in html
    assert "intent://" in html
    assert "wa.me" in html
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_share_template.py tests/test_share_context.py -q`
Expected: PASS

- [ ] **Step 5: Full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add app/web/templates/share.html tests/test_share_template.py
git commit -m "feat(share): redesign share page with app deep-link CTA"
```

---

## Verification Checklist (before any push)

- [ ] `.venv/bin/python -m pytest -q` green.
- [ ] `share_context` includes sender fields with fallbacks.
- [ ] `share.html` renders header (masjid + verified + WhatsApp), full-bleed media + play, footer (sender + time + Follow/Share).
- [ ] Follow Masjid: Android `intent://` + Play fallback; iOS deep link + App Store fallback; desktop → Play Store.
- [ ] Share copies/shares the URL; WhatsApp opens `wa.me`.
- [ ] Expired/unavailable share states unchanged.
- [ ] Do NOT push without the user's chosen branch.
