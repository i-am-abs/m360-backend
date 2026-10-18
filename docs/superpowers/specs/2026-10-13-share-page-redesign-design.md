# Share Page Redesign — Design

Date: 2026-10-13
Status: Approved for planning
Repo: `m360-backend` (server-rendered `/s/{id}` page)

## Summary

Redesign the server-rendered public share page (`app/web/templates/share.html`) to match the
new mobile design, and make the primary CTA open the app via deep link with a store fallback
when the app is not installed.

## Goals

- Match the new portrait layout: masjid header with verified badge and WhatsApp share button,
  full-bleed media with a centered play control, and a footer card with sender info + two CTAs.
- Make **Follow Masjid** open the app deep link; if the app is not installed, fall back to the
  platform store.
- Keep **Share** as native share/clipboard and the top-right button as WhatsApp share.
- Preserve existing OG metadata, expired/unavailable share states, and the HLS video player.

## Non-Goals

- No change to the `/s/{id}` gating logic (expired / sharing-disabled states).
- No change to the share link generation in the Flutter app.
- No new backend endpoints.

## Data Changes (`app/web/share_context.py`)

Add sender fields from the message document (`message.sender`):
- `sender_name` = `sender.name` (fallback: "Admin")
- `sender_role` = `sender.role` (fallback: "Admin")
- `sender_avatar_url` = `sender.avatar_url` (fallback: masjid avatar or default)

Existing fields stay: `message_id`, `masjid_name`, `masjid_location`, `masjid_verified`,
`masjid_avatar_url`, `is_video`, `video_hls_url`, `poster_url`, `og_image_url`,
`og_description`, `page_title`, `relative_time`, `canonical_url`, `deep_link_path`,
`share_host`, `play_store_url`, `app_store_url`, `android_package`, `marketing_site_url`.

## Layout (`app/web/templates/share.html`)

Portrait, full-height mobile layout:

1. **Header** (white):
   - Masjid avatar (circle) + masjid name; a blue verified badge when `masjid_verified`.
   - Subtitle: `masjid_location`.
   - Right: circular green **WhatsApp** button.
2. **Media** (flex-fills the space between header and footer, full-bleed):
   - Poster image (or a dark placeholder if none).
   - Centered play button; tapping plays the HLS video inline using the existing
     hls.js / native-HLS logic.
   - If `is_video` is false, show the poster/image only (no play button).
3. **Footer** (white card, rounded top):
   - Sender avatar + `sender_role` + blue verified badge + `sender_name`.
   - Right-aligned `relative_time` (e.g. "2 hrs ago").
   - Buttons row:
     - **Follow Masjid** — primary green gradient, person-plus icon.
     - **Share** — outlined, share icon.

## CTA Behavior

- **Follow Masjid** → open the app deep link, falling back to the store:
  - Android:
    `intent://<share_host><deep_link_path>#Intent;scheme=https;package=<android_package>;S.browser_fallback_url=<play_store_url>;end`
  - iOS: navigate to `https://<share_host><deep_link_path>`; if the page is still visible
    after ~1.2s, redirect to `app_store_url`.
  - Desktop/other: go directly to `play_store_url`.
- **Share** → `navigator.share({url})` when available, otherwise copy the URL to the clipboard
  and show the existing toast.
- **WhatsApp** → `https://wa.me/?text=<url-encoded caption + page URL>`.

## Edge Cases

- No video → no play button; poster fills the media area.
- Missing sender info → role/name fall back to "Admin"; missing sender avatar → masjid avatar.
- No poster → dark placeholder behind the play button.
- Existing expired (`share_expired.html`) and sharing-disabled (`share_unavailable.html`)
  pages keep their current behavior.
- OG tags (`og:*`, `twitter:*`) keep using the masjid/text thumbnail metadata (unchanged).

## Testing

- `tests/test_share_context.py`:
  - sender fields present when the message has a sender;
  - fallbacks ("Admin", masjid avatar) when missing.
- Template render smoke test for `share.html`:
  - asserts masjid name, sender role/name, and the Follow/Share/WhatsApp controls render.
- Existing expired/unavailable and OG tests stay green.

## Out of Scope

- Following the masjid directly (the app handles that after the deep link).
- Server-side detection of whether the app is installed (impossible; use the
  intent/timer fallback approach).
