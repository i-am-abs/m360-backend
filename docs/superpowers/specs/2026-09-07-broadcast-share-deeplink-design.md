# Broadcast Share Page + Deep Linking — Design Spec

**Date:** 2026-09-07
**Status:** Approved for planning
**Branches:** `feat/broadcast-share-deeplink` in both `m360-backend` (off `origin/main`) and `m360-flutter-app` (off `origin/v3`)

---

## 1. Problem

When a user shares a masjid broadcast (announcement video) from the Flutter app, we currently
share the **raw Mux HLS URL** (`https://stream.mux.com/{id}.m3u8`) as plain text. This:

- looks broken in WhatsApp / social (no preview, `.m3u8` won't play for most recipients);
- gives recipients no path back into the app or the specific masjid;
- carries no branding or context (which masjid, what announcement).

We want:

1. **A proper shareable web page** at a stable HTTPS URL that plays the video, shows the
   masjid, and has a call-to-action — matching the approved screenshot design.
2. **Deep linking** from that page (and from the link itself) into the app: open the
   specific masjid's announcement feed if the app is installed; otherwise send the user to
   the Play Store / App Store. "Back" from the announcement feed unwinds to the masjid
   detail page and then the masjid list.
3. **Rich link previews** — when the URL is pasted into WhatsApp / X / Facebook / iMessage,
   it renders a card with the video thumbnail, masjid name, and announcement text.

---

## 2. Scope

### In scope

- New public, server-rendered share page in `m360-backend` (`app/web/`).
- Open Graph / Twitter Card metadata on that page.
- Android App Links + iOS Universal Links: `.well-known` association files served by the
  backend; intent-filter / entitlement wiring in the Flutter app.
- Flutter `DeepLinkService` that resolves an incoming `/s/{messageId}` link to a masjid and
  builds the navigation stack.
- Replacing the shared text in the 3 Flutter share call-sites with the new web URL.
- Configuration surface for domain, store URLs, signing fingerprints, Apple IDs.

### Out of scope (explicitly)

- **`m360-web`** (the standalone Next.js app) — left untouched.
- **Full deferred deep linking** — if the app is *not* installed, after store install the
  app opens to its normal home screen; the specific announcement target is **not**
  preserved through the install. (Best-effort only, per decision.)
- Making the in-app broadcast feed publicly viewable — a logged-out user who deep-links in
  is routed through the **login screen** first, then lands on the announcement feed
  (per decision).
- Analytics/attribution beyond the existing `AnalyticsService.trackShareAnnouncement()`.
- iOS App Store submission / the numeric App Store ID (provided later by the owner).

---

## 3. External inputs required from the project owner

These are needed for the feature to fully function in production. The implementation will
use **config placeholders** with safe defaults so nothing breaks before they are supplied.

| Input | Used for | Default until provided |
| --- | --- | --- |
| Final subdomain (e.g. `share.vyapari.link`) + DNS → backend | Everything | `share.vyapari.link` placeholder in config |
| Android **release** signing cert **SHA-256 fingerprint(s)** | `assetlinks.json` | empty list (App Links won't verify, link still opens page) |
| Apple **Team ID** (10 chars) | `apple-app-site-association`, iOS entitlement | `TEAMID` placeholder |
| Apple **bundle ID** | AASA (`com.starkinnovations.m360`, already known) | known |
| **App Store numeric ID** (once iOS is published) | App Store fallback URL | falls back to a search URL |

---

## 4. Architecture

```
WhatsApp / X / iMessage
        │  (link pasted)
        ▼
https://share.vyapari.link/s/{messageId}
        │
        ├──► GET /s/{messageId}                     → server-rendered HTML (Jinja2)
        │        ├─ <meta og:*> / <meta twitter:*>  → rich preview card
        │        ├─ <video> + hls.js                → playable video, poster = Mux thumbnail
        │        ├─ "Follow Masjid" CTA + play tap  → smart-app-open JS
        │        └─ "Share" button                  → navigator.share / clipboard
        │
        ├──► GET /.well-known/assetlinks.json               → Android App Links
        └──► GET /.well-known/apple-app-site-association     → iOS Universal Links

App installed  ─────────────────────────────────────────────┐
        │  OS intercepts the verified https link            │
        ▼                                                    │
Flutter DeepLinkService                                      │
  parse /s/{messageId}                                       │
  → GET /api/v1/broadcast/public/{messageId}  (masjid_id)    │
  → MasjidEntityService.getMasjid(masjid_id)  (masjid obj)   │
  → if not logged in: LoginScreen(return → feed)             │
  → build stack:  Masjid tab                                 │
                  └─ MasjidDetailsScreen(masjid)             │
                     └─ BroadcastFeedScreen(masjidId, …)  ◄──┘
                        (back → details → masjid list)

App NOT installed
        │  smart-app-open JS timeout fires
        ▼
Play Store / App Store  →  install  →  app opens to normal home
```

All server-side code is in `m360-backend`. Flutter changes are additive.

---

## 5. Backend design (`m360-backend`)

### 5.1 New router: `app/web/share.py`

A plain `APIRouter` (no `/admin` prefix, no auth), mounted in `app/factory.py`
**outside** the `settings.admin_panel_enabled` block and **outside** the `/api/v1` prefix
(the `.well-known` paths must sit at the domain root).

| Route | Response | Notes |
| --- | --- | --- |
| `GET /s/{message_id}` | `HTMLResponse` from Jinja2 `share.html`; renders a styled **"announcement not found"** page with 404 status when the message is missing/deleted | `Cache-Control: public, max-age=300` on success |
| `GET /.well-known/assetlinks.json` | `JSONResponse` (list form) built from config | `Content-Type: application/json` |
| `GET /.well-known/apple-app-site-association` | `Response` with explicit `media_type="application/json"`, **no `.json` extension in path** | body built from config |

The router reuses the existing `Environment(FileSystemLoader("app/web/templates"))` pattern
from `app/web/router.py` (a shared `templates` object can be lifted into
`app/web/__init__.py` or a small `app/web/templating.py` so both routers use one env — a
targeted cleanup, not a rewrite).

### 5.2 Data for the share page

Extend the existing public endpoint's data path. `GET /api/v1/broadcast/public/{message_id}`
(`app/api/v1/endpoints/broadcast.py:28`) currently returns:

```json
{ "message": { …raw message… },
  "masjid":  { "name": "", "city": "", "address": "" } }
```

Add to the `masjid` object: `state`, `verified` (derived from
`masjid.management.is_claimed`), `photo_url` (already derived flat by
`MongoMasjidRepository`, else `photos[0].url`), and `place_id`. The `message` already
carries `video_url`, `thumbnail_url`, `text`, `message_type`, `created_at`.

The **share page route** calls the same service methods directly (no HTTP self-call):
`BroadcastFeedService.get_message_raw(message_id)` + `MasjidEntityService.get_masjid(...)`.
A thin helper assembles a `SharePageContext` dataclass/dict for the template:

| Field | Source | Fallback |
| --- | --- | --- |
| `masjid_name` | masjid.name | "This masjid" |
| `masjid_location` | `", ".join(filter(city, state))` | address, else "" |
| `masjid_verified` | `management.is_claimed` | `false` |
| `masjid_avatar_url` | masjid photo_url | app logo asset |
| `video_hls_url` | `message.video_url` | — (image-only message → hide player) |
| `poster_url` | `message.thumbnail_url` | app OG default asset |
| `og_image_url` | `thumbnail_url` + `?width=1200&height=630&fit_mode=smartcrop` when it is a `image.mux.com` URL | static default |
| `announcement_text` | `message.text` (trimmed to ~200 chars for description) | "New announcement from {masjid_name}" |
| `relative_time` | humanized `now - created_at` (e.g. "2 hrs ago") | "" |
| `message_id` | path param | — |
| `deep_link_path` | `/s/{message_id}` | — |

### 5.3 Template: `app/web/templates/share.html`

Standalone (does **not** extend `admin_base.html`). Matches the approved screenshot:

- **Header bar** (white): app logo (green rounded tile) + "Powered by **Muslim 360**"
  on the left; an **X** button on the right linking to the marketing site / app root.
- **Media area** (full-bleed, tall): `<video controls playsinline poster="{{poster_url}}">`
  with a centered circular **play-button overlay**. On first tap/click:
  - if `Hls.isSupported()` → lazy-load **hls.js** from CDN, attach `video_hls_url`;
  - else (Safari / iOS) → set `<video src>` to the HLS URL directly (native support);
  - then `video.play()` and hide the overlay.
  Non-video messages: render the image instead of the player.
- **Bottom card** (white, rounded top): circular masjid avatar, masjid name +
  inline **verified check** (only when `masjid_verified`), `masjid_location` subtitle,
  `relative_time` right-aligned.
- **Buttons row**:
  - **Follow Masjid** — primary (green gradient, `+` icon) → `openApp()` JS.
  - **Share** — outline (send icon) → `navigator.share({title, text, url})` with
    `navigator.clipboard.writeText` + toast fallback.
- Fonts: Plus Jakarta Sans (web font or system fallback stack). Colors from the app
  palette (`#45D07C` / `#61D47D→#ADFF8D` gradient, text `#091914`, muted `#5D6C67`).
- All CSS inline in a `<style>` block in the template (no build step in `app/web`).

### 5.4 Meta tags (in `<head>`)

```html
<title>{{masjid_name}} — announcement | Muslim 360</title>
<meta name="description" content="{{announcement_text_short}}">

<meta property="og:site_name" content="Muslim 360">
<meta property="og:title" content="{{masjid_name}}">
<meta property="og:description" content="{{announcement_text_short}}">
<meta property="og:type" content="video.other">
<meta property="og:url" content="{{canonical_url}}">
<meta property="og:image" content="{{og_image_url}}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:video" content="{{video_hls_url}}">
<meta property="og:video:type" content="application/x-mpegURL">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{masjid_name}}">
<meta name="twitter:description" content="{{announcement_text_short}}">
<meta name="twitter:image" content="{{og_image_url}}">
```

> WhatsApp uses `og:title` + `og:description` + `og:image`; the sized Mux thumbnail
> (`image.mux.com/{playbackId}/thumbnail.jpg?width=1200&height=630&fit_mode=smartcrop`)
> renders a proper large card.

### 5.5 Smart app-open JavaScript (inline)

```
function openApp() {
  var path = "{{deep_link_path}}";                       // "/s/{id}"
  var httpsUrl = "https://{{share_host}}" + path;
  var ua = navigator.userAgent || "";
  var now = Date.now();
  var storeUrl = /android/i.test(ua) ? "{{play_store_url}}"
               : /iphone|ipad|ipod/i.test(ua) ? "{{app_store_url}}"
               : "{{play_store_url}}";
  // Try to hand off to the app; if still here after ~1.2s, go to the store.
  setTimeout(function () {
    if (Date.now() - now < 1600) window.location = storeUrl;
  }, 1200);
  if (/android/i.test(ua)) {
    window.location = "intent://{{share_host}}" + path +
      "#Intent;scheme=https;package={{android_package}};S.browser_fallback_url=" +
      encodeURIComponent(storeUrl) + ";end";
  } else {
    window.location = httpsUrl;   // iOS Universal Link handoff
  }
}
```

### 5.6 `.well-known` payloads

`assetlinks.json`:

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "{{android_package}}",
    "sha256_cert_fingerprints": [ …from config… ]
  }
}]
```

`apple-app-site-association`:

```json
{
  "applinks": {
    "apps": [],
    "details": [{
      "appID": "{{apple_team_id}}.{{apple_bundle_id}}",
      "paths": ["/s/*"]
    }]
  }
}
```

### 5.7 Config additions — `app/core/config.py` (`.env`)

| Setting | Type | Default |
| --- | --- | --- |
| `share_web_base_url` | `str` | `https://share.vyapari.link` |
| `android_package_name` | `str` | `com.starkinnovations.m360` |
| `android_sha256_cert_fingerprints` | `list[str]` (comma-split) | `[]` |
| `apple_team_id` | `str` | `""` |
| `apple_bundle_id` | `str` | `com.starkinnovations.m360` |
| `play_store_url` | `str` | `https://play.google.com/store/apps/details?id=com.starkinnovations.m360` |
| `app_store_url` | `str` | `https://apps.apple.com/app/muslim-360/id000000000` (search fallback until real ID) |
| `marketing_site_url` | `str` | `https://muslim360.app` |

### 5.8 `app/factory.py` change

Add, unconditionally (before or after the admin block, not inside it):

```python
from app.web.share import router as share_router
application.include_router(share_router)
```

Confirm `NormalizePathMiddleware` does not strip/rewrite `/.well-known/...` or the
extension-less AASA path (check `app/middleware/normalize_path.py` during implementation;
add an exemption if needed).

---

## 6. Flutter design (`m360-flutter-app`)

### 6.1 Dependency

`pubspec.yaml`: add `app_links: ^6.x` (actively maintained successor to `uni_links`).
Run `flutter pub get`.

### 6.2 Android — `android/app/src/main/AndroidManifest.xml`

Add to the **main launcher activity** (`.MainActivity`):

```xml
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https"
        android:host="share.vyapari.link"
        android:pathPrefix="/s" />
</intent-filter>
```

(Host string must match final config value. `assetlinks.json` must be reachable at
`https://<host>/.well-known/assetlinks.json` for `autoVerify` to pass.)

### 6.3 iOS

- New file `ios/Runner/Runner.entitlements`:

  ```xml
  <key>com.apple.developer.associated-domains</key>
  <array><string>applinks:share.vyapari.link</string></array>
  ```

- Reference it from `ios/Runner.xcodeproj/project.pbxproj`
  (`CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;` in each build config).
- `Info.plist`: `FlutterDeepLinkingEnabled` is **not** set to `true` — we handle links
  manually via `app_links` so we control the navigation stack.

### 6.4 New service — `lib/services/deep_link_service.dart`

Responsibilities:

- `init()` — called from `main.dart` after `StoreManager` bootstrap. Subscribes to
  `AppLinks().uriLinkStream`; also awaits `AppLinks().getInitialLink()` for cold start.
- **Parse** — `parseShareLink(Uri) -> String? messageId`: accept host == configured share
  host, path matching `^/s/([A-Za-z0-9_-]+)/?$`. Anything else → `null` (ignored).
- **Queue** — if the app is still bootstrapping / no `NavigatorState` yet, store the
  pending `messageId` and replay it once the first frame is up and `NavigationService`
  has a context.
- **Resolve & navigate** — `_openAnnouncement(messageId)`:
  1. `GET /api/v1/broadcast/public/{messageId}` (new method on `BroadcastService`,
     unauthenticated) → `masjid_id` (+ `masjid_name`, `follower_count` if available).
  2. `MasjidEntityService.instance.getMasjid(masjidId)` → masjid entity.
  3. If `StoreManager` has no auth token → navigate to `LoginScreen` with
     `return_route`/args that resume `_openAnnouncement(messageId)` post-login
     (reuse existing `return_route` / `pop_on_success` login-args pattern from
     `routes.dart`).
  4. Build the stack with `NavigationService` (global navigator key):
     - ensure the **Masjid tab** of `BottomNav` is selected;
     - `push(MaterialPageRoute(MasjidDetailsScreen(masjid: masjid, hasDetails: true)))`;
     - `push(MaterialPageRoute(BroadcastFeedScreen(masjidId: …, masjidName: …,
       followerCount: …, masjidPhotoUrl: …)))`.
     Result: **Back** → masjid details → Masjid tab (list). Matches requirement.
  5. Errors (network, 404, deleted) → land on the Masjid tab and show a snackbar
     ("This announcement is no longer available").
- Log `AnalyticsService` screen/event for deep-link open.

### 6.5 `main.dart`

After Firebase init + `StoreManager` load + `runApp`, call
`DeepLinkService.instance.init()` (guarded so it only runs once). The service defers actual
navigation until `WidgetsBinding.instance.addPostFrameCallback`.

### 6.6 Replace the Mux link in shares

- Add `SHARE_BASE_URL` to `.env.dev` (and document it for `.env.staging` / `.env.prod`).
- New helper: `BroadcastService.instance.shareUrlFor(String messageId)` →
  `"${dotenv.env['SHARE_BASE_URL']}/s/$messageId"` (fallback to the config default host if
  the env key is absent).
- Update the 3 call-sites to share **`'$text\n\n$shareUrl'`** instead of the video URL:
  - `lib/features/home/screens/broadcast/broadcast_feed.dart:346` (`_shareMessage`) —
    real `msg.id`.
  - `lib/features/home/widgets/broadcast_message_card.dart:584` (`_share`) — needs the
    message id threaded into the widget (add a `messageId` field; the card is built from a
    `BroadcastMessage` in `broadcast_feed.dart`, so pass `msg.id`).
  - `lib/features/home/screens/masjid/masjid_broadcast.dart:645` (`_sharePost`) — this
    screen still renders **sample/mock** posts (`_BroadcastPost` has an `id` but the list
    is hardcoded sample data). Wire `shareUrlFor(post.id)` where an id exists; leave a
    `// TODO` note that this screen needs real API data before its share is meaningful.

---

## 7. Isolation / boundaries

| Unit | Responsibility | Depends on | Consumers |
| --- | --- | --- | --- |
| `app/web/share.py` | HTTP routes for share page + `.well-known` | `BroadcastFeedService`, `MasjidEntityService`, `templates`, `settings` | FastAPI app (`factory.py`) |
| `SharePageContext` builder | Shape raw message + masjid into template fields | services above | `share.py` only |
| `share.html` | Presentation | context dict | — |
| `.well-known` builders | Serialize config → association JSON | `settings` | `share.py` |
| `DeepLinkService` (Flutter) | Receive link → resolve → navigate | `AppLinks`, `BroadcastService`, `MasjidEntityService`, `NavigationService`, `StoreManager` | `main.dart` |
| `parseShareLink` (pure fn) | `Uri` → `messageId?` | none | `DeepLinkService`, tests |
| `BroadcastService.shareUrlFor` | messageId → URL string | dotenv | 3 share call-sites |

`parseShareLink` and the `SharePageContext` builder are pure and independently unit-tested.

---

## 8. Error handling

| Case | Backend | Flutter |
| --- | --- | --- |
| Message id unknown / deleted | `/s/{id}` → styled 404 page ("announcement no longer available", link to app) | snackbar on Masjid tab |
| Masjid lookup fails | render page with masjid fields blank/fallbacks; still show video | proceed to feed if `masjid_id` known; else snackbar |
| Mux thumbnail missing | `og:image` → static default asset; `<video>` has no poster | n/a |
| HLS unsupported in browser | native `<video src>` attempt; if it fails, show "Open in app" prompt | n/a |
| Deep link while logged out | n/a | route to `LoginScreen`, resume after success |
| Deep link during cold start | n/a | queue messageId, replay after first frame |
| `assetlinks`/AASA not yet configured (empty fingerprints / placeholder Team ID) | files still served (valid JSON, no real targets) → link opens the **web page** instead of the app; no crash | n/a |
| Malformed link (`/s/`, `/s/../x`, other host) | n/a | `parseShareLink` returns null, link ignored |

---

## 9. Testing

### Backend (pytest, `tests/`)

- `GET /s/{valid_id}` → 200, body contains `og:title`, `og:image`, `twitter:card`,
  the masjid name, and the HLS URL.
- `GET /s/{missing_id}` → 404 + "not available" copy.
- `GET /.well-known/assetlinks.json` → 200, `application/json`, list with
  `delegate_permission/common.handle_all_urls` and the configured package.
- `GET /.well-known/apple-app-site-association` → 200, `application/json`,
  `applinks.details[0].paths == ["/s/*"]`.
- `SharePageContext` builder: unit tests for location joining, verified derivation,
  text truncation, Mux thumbnail sizing, fallbacks.

### Flutter (`flutter test`)

- `parseShareLink`: table test — valid `/s/abc123` → `"abc123"`; trailing slash ok;
  wrong host → null; `/s/` → null; `/other` → null.
- Navigation-stack builder with a mocked `BroadcastService` + `MasjidEntityService`:
  asserts the pushed route sequence (details then feed) and that logged-out routes to
  login first.

### Manual (requires deployed domain + real fingerprints/IDs)

- `adb shell am start -W -a android.intent.action.VIEW -d "https://<host>/s/<id>"`
  → app opens to the announcement feed.
- iOS: tap the link from Notes / Messages → app opens to the feed.
- Paste URL into WhatsApp, X, iMessage → preview card shows thumbnail + masjid name.
- App-not-installed: open link in mobile browser → "Follow Masjid" → store page.
- `https://search.google.com/test/rich-results` / Facebook Sharing Debugger on the URL.
- `https://<host>/.well-known/assetlinks.json` validates in Google's
  Statement List Generator and Tester.

---

## 10. Rollout / sequencing

1. **Backend**: config + `share.py` + template + `.well-known` + `factory.py` wiring +
   `broadcast/public` payload extension + tests. Deployable independently; `/s/{id}`
   works as a web page immediately.
2. **DNS**: owner points `share.vyapari.link` → backend; owner supplies SHA-256
   fingerprint(s) and Apple Team ID → config.
3. **Flutter**: `app_links` + manifest/entitlement + `DeepLinkService` + `main.dart` +
   `shareUrlFor` + 3 call-site edits + tests.
4. **Verify** App Links / Universal Links on real devices; run through the manual
   checklist.
5. Merge `feat/broadcast-share-deeplink` in each repo per that repo's normal flow
   (backend → `main`, flutter → `v3`).

Stashed WIP to restore afterwards:
- backend: `git checkout fix/donations-off-by-default && git stash pop`
- flutter: `git checkout v3 && git stash pop`

---

## 11. Open questions / assumptions

- **Assumption:** "verified" badge = `masjid.management.is_claimed == true`. If there is a
  dedicated verification flag, use that instead (confirm during implementation).
- **Assumption:** `BroadcastService.getFeed` requires auth (endpoint uses
  `get_current_user`), hence the login redirect. If a public feed endpoint is added later,
  the logged-out path can skip login.
- **Assumption:** `MasjidEntityService.instance.getMasjid(id)` accepts the `masjid_id`
  returned by `broadcast/public` (same id space). Verify; add a translation if the public
  endpoint returns an internal id vs `place_id`.
- **App Store ID** unknown → App Store fallback uses a search/landing URL until provided.
