# Mux Data Video Analytics — Design

Date: 2026-10-23
Status: Approved for planning
Repos: `m360-backend`, `m360-flutter-app`

## Problem

Mux dashboards show null/zero engagement despite real views. Mux Data is a
**client-side** SDK; the current players (native `video_player`/Chewie in the app, raw
hls.js/`<video>` on the share page) never call `mux.monitor(...)`, so no views are
reported. Historical views will not backfill.

## Goal

Instrument playback with Mux Data so views, watch time, rebuffering, startup time, and
errors appear in the Mux dashboard, for both the public share page and the Flutter app.

## Decisions (approved)

- `video_id` = the **Mux playback ID** (so Mux attributes views to the asset).
- `video_title` = "<masjid> announcement"; `sub_property_id` = masjid place id
  (grouping per masjid); `player_name` = `m360-share-page` / `m360-app`;
  `video_stream_type` = `on-demand`; `env_key` = `MUX_ENV_KEY`.
- Web: keep the existing custom player UI; add `mux-embed` and call `mux.monitor` for
  both the hls.js path and the native-HLS path.
- Flutter: no native SDK; load a minimal server-rendered **embed page** in a
  `webview_flutter` WebView (reuses the web player + Mux Data).

## Non-Goals

- No native Mux Data SDK bridge.
- No changes to upload/webhook flows.
- No backfill of historical metrics.

## Backend

1. `share_context.py`: add
   - `mux_env_key` (`settings.mux_env_key`),
   - `mux_playback_id` (`message.mux_playback_id`),
   - `analytics_title` = f"{masjid_name} announcement",
   - `analytics_sub_property_id` = place id.
2. `share.html`: load `https://src.litix.io/core/4/mux.js` (guard `typeof mux`); on play:
   - hls.js path: `mux.monitor(v, { hlsjs: hls, Hls, data: { env_key, video_id: mux_playback_id, video_title, player_name: 'm360-share-page', sub_property_id, video_stream_type: 'on-demand', player_init_time } })`
   - native-HLS path: `mux.monitor(v, { data: {...same...} })`
3. New `GET /embed/{message_id}` → minimal `share_embed.html` (full-screen black player
   only, same monitoring, `player_name: 'm360-app'`). Gated by `resolve_share_state`:
   expired/unavailable → 404 minimal page. Extract the player JS into a Jinja partial
   shared by both pages.

## Flutter

1. Add `webview_flutter`.
2. `BroadcastVideoPlayer` gains `messageId`; builds `<origin>/embed/{id}?user_id=<id>`
   where origin = `API_BASE_URL` minus `/api/v1`; renders a full-screen `WebViewWidget`
   (JS unrestricted; Android media playback allowed).
3. `broadcast_message_card.dart` passes `messageId`.
4. Fallback: WebView load error → poster + open-in-browser.

## Privacy

Mux Data uses an analytics cookie. Default to normal cookies; `disableCookies` can be
enabled later if required.

## Testing

- Backend: context exposes the Mux env key + playback id + metadata; both templates
  contain the mux script and a `monitor` call; embed route 404s for gated posts.
- Flutter: a pure helper builds the embed URL from `API_BASE_URL`; widget/analyze pass.
