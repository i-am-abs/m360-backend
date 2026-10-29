# Share Analytics & Attribution — Design

**Date:** 2026-10-29
**Status:** Approved for implementation
**Scope:** Backend (share registry + page context), web share page & embed player, Android app

## 1. Goals

Instrument the announcement-sharing funnel end to end so we can answer:

- How many people open a shared announcement, and where they came from.
- How much of the video they watch (start → 25 → 50 → 75 → complete).
- Which shares drive `View Masjid` taps and masjid page opens.
- How often the app is not installed and users fall back to the Play Store.

The event names, triggers and attributes are defined in
`docs/M360 - app events.csv` (source of truth).

**Non-goals**

- No changes to existing Firebase Analytics events.
- No ad-tech, no cross-site tracking, no cookie-based attribution.
- No server-side Mixpanel export/ETL in this phase.

## 2. Decisions

| Decision | Choice |
|---|---|
| Analytics destination | Mixpanel for these events; Firebase untouched |
| Share identity | Backend-issued `share_id` (registry), not client-generated |
| Identity | `distinct_id` = anonymous device/visitor UUID; `user_id` is a property when known; no alias/identify |
| Playback events | Emitted from the embed player for both web and in-app WebView |
| In-app context | Passed to the embed in the URL **fragment** so ids never reach server logs |

## 3. Architecture

Three units with narrow responsibilities:

1. **Share registry (backend)** — creates and stores share links, owns the
   `share_id` / `root_share_id` / `parent_share_id` chain, and exposes the chain
   to the rendered page.
2. **Web analytics (landing + embed)** — reads attribution from the URL,
   resolves `anonymous_visitor_id`, and emits the funnel events to Mixpanel.
3. **App analytics (Flutter)** — emits the app-side events (`click_on_share_announcement`,
   `masjid_deep_link_opened`) and supplies identity/journey context to the embed.

Analytics must never block or break the user journey: every call is
fire-and-forget and failures are swallowed.

## 4. Data model — `shares`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | internal |
| `share_id` | string (uuid4) | public identifier, used in URLs |
| `message_id` | string | announcement id |
| `masjid_id` | string | masjid place id |
| `masjid_name` | string | denormalised for reporting |
| `video_id` | string | equal to `message_id` |
| `mux_playback_id` | string \| null | correlation with Mux Data |
| `root_share_id` | string | first share in the chain |
| `parent_share_id` | string \| null | the share this one was created from |
| `created_by_user_id` | string \| null | app users only |
| `channel` | enum | `android_native_share_sheet` \| `web_native_share_sheet` |
| `platform` | enum | `android_app` \| `mobile_web` \| `desktop_web` |
| `utm_source`, `utm_medium`, `utm_campaign` | string \| null | optional, copied onto the URL |
| `created_at` | ISO string | |

**Indexes:** unique `share_id`; `(message_id, created_at)`; `root_share_id`.

## 5. API

### `POST /api/v1/shares` (auth optional)

Request:

```json
{
  "message_id": "6a9f...",
  "parent_share_id": "uuid | null",
  "channel": "android_native_share_sheet | web_native_share_sheet",
  "platform": "android_app | mobile_web | desktop_web",
  "utm_source": "whatsapp | null",
  "utm_medium": "social | null",
  "utm_campaign": "string | null"
}
```

Behaviour:

1. Load the announcement; 404 if missing.
2. 409 if `resolve_share_state(message) != "available"` (sharing disabled or expired).
3. If `parent_share_id` is supplied, load it; 422 if it belongs to a different
   message; `root_share_id` = parent's root, otherwise `root_share_id` = new id.
4. Insert the record and return:

```json
{
  "share_id": "…",
  "root_share_id": "…",
  "parent_share_id": "… | null",
  "url": "https://muslim360.in/s/{message_id}?share={share_id}"
}
```

The `url` includes UTM parameters when supplied.

### `GET /s/{message_id}?share=…`

- Looks up the share record and passes `share_id`, `root_share_id`,
  `parent_share_id`, and UTM values into the template context.
- An unknown or malformed `share` value is tolerated: the page still renders
  with null attribution (no error), because links may be shared around or DB
  records pruned.

### Deep links

Unchanged shape, extended with query parameters:

```
https://muslim360.in/m/{place_id}?j={journey_id}&s={share_id}
```

`journey_id` is generated client-side on the web `View Masjid` tap;
`share_id` is the share the visitor arrived from. Both are carried through the
Play Store install referrer for deferred installs.

## 6. Web events

**Setup**

- Mixpanel JS with `MIXPANEL_TOKEN` and `MIXPANEL_API_HOST` from settings.
  Empty token → all calls are no-ops.
- `anonymous_visitor_id` = UUID persisted in `localStorage` (`m360_visitor_id`).
- `platform` = `mobile_web` / `desktop_web` by UA; `android_app` when the embed URL
  carries `for_app=1` (the app WebView).
- Super properties: `video_id`, `video_title`, `masjid_id`, `masjid_name`,
  `share_id`, `root_share_id`, `parent_share_id`, `anonymous_visitor_id`,
  `utm_*`, `platform`; `user_id` when passed in the fragment.

**Landing page (`/s/{id}`)**

| Event | Trigger |
|---|---|
| `video_landing_page_viewed` | analytics initialises after load |
| `video_playback_started` | first `playing` event (not the Play tap) |
| `video_playback_25_percent` | `currentTime / duration` first ≥ 0.25 |
| `video_playback_50_percent` | first ≥ 0.50 |
| `video_playback_75_percent` | first ≥ 0.75 |
| `video_playback_completed` | native `ended` only (seeking to the end does not count) |
| `video_playback_error` | fatal player/HLS error → `error_code`, `error_type`, sanitized message |
| `click_on_view_masjid_cta` | CTA tap; generates `journey_id`, appends `?j=…&s=…` |
| `click_on_share_announcement` | Share tap; creates a child share (`channel=web_native_share_sheet`), emits, then opens the native sheet with the tracked URL |
| `redirect_to_play_store` | immediately before the Play Store redirect; `redirect_destination=google_play_store`, `redirect_reason` = `app_not_opened` \| `app_not_installed` |

Milestones fire at most once per playback session. A session begins on the
first `playing` after page load and again after a natural `ended`; seeking
does not start a new session or re-arm the marks.

**Embed (`/embed/{id}`)**

- Same playback events (`started`, 25/50/75, completed, error) with
  `platform=android_app` and Mux fields.
- In-app context arrives in the fragment: `#v=<visitor>&u=<user_id>&j=<journey>&s=<share>`.
- Bot/crawler UAs (`navigator.webdriver`, common crawler tokens) skip events.

## 7. App events

**SDK**

- `mixpanel_flutter` wrapped in `MixpanelService` (fire-and-forget).
- `distinct_id` = persisted device UUID (`m360_device_id`).
- Super properties: `platform=android_app`, `app_version`, `anonymous_visitor_id`.
- `user_id` registered as a property when the user is logged in.

**`click_on_share_announcement`**

1. On Share tap, call `POST /api/v1/shares` with `message_id`,
   `parent_share_id` (from the incoming link for this screen, kept for the
   session), `channel=android_native_share_sheet`, `platform=android_app`.
2. Emit the event with `share_id`, `root_share_id`, `parent_share_id`.
3. Open the native sheet with the tracked URL.
4. If the API call fails (timeout 2 s), open the sheet with the plain
   `/s/{message_id}` URL and emit without ids.

**`masjid_deep_link_opened`**

- Parse `j` and `s` from `/m/{place_id}` (direct and deferred).
- After `MasjidDetailsScreen` is displayed, emit with `journey_id`, `share_id`,
  `masjid_id`, `masjid_name`, `video_id` (when known), `deep_link_source=shared_video_webpage`,
  `platform=android_app`, `app_version`, `user_id`.

**In-app playback**

- The WebView loads `/embed/{id}?for_app=1#v=<device_id>&u=<user_id>&j=<journey>&s=<share>`.
- Playback events are emitted by the embed (Section 6), so no native playback
  instrumentation is added.

## 8. Privacy

The policy currently names Firebase only. Update:
- “Data Sharing” lists Mixpanel as a service provider (event analytics).
- “App Usage & Diagnostics” mentions anonymous product events sent to Mixpanel.
- No advertising identifiers, no cross-site tracking; `anonymous_visitor_id` is
  a random UUID, not a fingerprint.
- Bump “Last updated”.

## 9. Error handling

- Analytics: wrapped in try/catch; failures never surface to the user.
- Share API: 2 s timeout on the app; the share sheet always opens.
- Share page: unknown `share` id → null attribution, page renders normally.
- Mixpanel unavailable → no-ops; playback is unaffected.

## 10. Testing

**Backend**
- New share: root = own id, parent null.
- Re-share: root inherited, parent = incoming id.
- Parent from another message rejected.
- Non-shareable / expired announcement rejected.
- Unknown `?share` id still renders the page with null attribution.
- Empty Mixpanel token → page renders without analytics config.

**App**
- Share request builder inherits `parent_share_id` from the incoming link.
- `j`/`s` parsed for direct and deferred links.
- API failure falls back to the plain URL and still shares.

**Web**
- Pure milestone function: 25/50/75 fire once; `ended` only on natural end;
  no completion on seek.

**Manual**
- Create a share chain (web → app re-share), open on a device, confirm events
  in Mixpanel Live View with the expected properties.

## 11. Rollout

1. Backend: registry, API, page context, privacy copy → deploy.
2. Web: landing + embed analytics → same deploy.
3. App: Mixpanel, share CTA, deep-link event → next app release.

## 12. Risks

- Mixpanel token/region must be supplied; until then the integration is inert.
- Share records grow unbounded; add a TTL or archival job only if volume
  warrants it (not in this phase).
- Deep-link attribution depends on Play Install Referrer, which remains
  Android-only.
