# Broadcast Expiry + Share Controls — Design

Date: 2026-10-10
Status: Approved for planning
Repos: `m360-backend`, `m360-flutter-app`

## Summary

Masjid committee members can publish announcements (video, and other types) to a
masjid's broadcast feed. Two new per-announcement controls are added at creation
time:

1. **Auto-delete (expiry)** — a single fixed toggle: "Auto-delete after 1 month"
   (30 days). When on, the post is automatically removed from the broadcast feed
   after 30 days and its public share link stops showing the post. When off
   (default), the post stays indefinitely.
2. **Share control** — a single toggle: "Do not allow sharing this video outside
   the app." When on, the in-app Share action is hidden for that post and its
   public share page is replaced with a "not available" page. When off (default),
   sharing works as it does today.

Both controls apply to **all** announcement types, though the current create
screen only produces video posts.

## Goals

- Let a committee member opt in to a 30-day auto-delete for a post.
- Let a committee member opt out of external sharing for a post.
- Make expiry and share-disable enforced on **both** the in-app feed and the
  server-rendered public share page (`/s/{id}`).
- Stay backward compatible: existing posts keep today's behavior.

## Non-Goals

- Custom/arbitrary expiry durations (fixed 30 days only).
- Editing expiry or share settings after a post is created.
- Countdown timers / live "time remaining" clocks.
- Hard-deleting the Mux video asset at expiry.
- Preventing screen-recording/copying (not technically enforceable); the control
  governs the in-app Share action and the public share page only.

## Decisions (from brainstorming)

| Question | Decision |
|----------|----------|
| Expiry selection | Single fixed 30-day toggle (`Auto-delete after 1 month`) |
| Default checkbox state | Both checkboxes **unchecked** by default (sharing allowed, no expiry) |
| What "do not allow sharing" blocks | Hide the in-app Share button **and** block the public `/s/{id}` page |
| Expiry enforcement | Soft expire: filter feeds by `expires_at`; keep the record (and Mux asset) so the share page can show an expired state |
| Scope of controls | All announcement types |
| Blocked share page (not expired) | A dedicated "not available" page with App Store / Play Store CTAs |
| Expiry note visibility | Visible to everyone in the feed |
| Checkbox wording | Generalize: "Do not allow sharing this video outside the app." |

## Data Model

Collection: `broadcast_messages` (already used by the rich feed and the share
page). Two new optional fields on every message:

- `allow_sharing: bool` — default `true`. When `false`, hide the in-app Share
  action for the post and replace its public `/s/{id}` page with a "not
  available" page.
- `expires_at: str | null` — ISO-8601 UTC string. `null` = never expires. Set to
  `created_at + 30 days` when the auto-delete toggle is on.

Legacy/system documents missing these fields are treated at read time as
`allow_sharing = true` and `expires_at = null` (no behavior change).

Indexes: add a sparse index on `expires_at` to keep the feed filter cheap.
Existing indexes (`masjid_id + created_at`, `masjid_id + updated_at`,
`sender.user_id`) are unchanged.

## Backend Behavior

### Create

`POST /masjids/{id}/broadcast` → `BroadcastFeedService.post_message`.

- Extend `BroadcastMessageCreate` with:
  - `allow_sharing: bool = True`
  - `expires_in_days: Optional[int] = None`
- The server is the source of truth for the timestamp: when `expires_in_days`
  is provided (only 30 is allowed for now), compute
  `expires_at = now(UTC) + 30 days`; otherwise `None`.
- `MongoBroadcastFeedRepository.create_message` persists `allow_sharing` and
  `expires_at`.
- The `BroadcastFeedRepository` interface and `MongoBroadcastFeedRepository` are
  updated accordingly. (NoOp store signature stays compatible.)

### Feed read

`MongoBroadcastFeedRepository.get_messages`:

- Add filter: include a message when `expires_at` is null **or**
  `expires_at > now`. Expired posts never appear in the feed for anyone.
- Apply the same filter to every read path (initial load, `before` cursor, and
  `since` refresh) so an expiring post disappears everywhere at once.
- Message payload returned to the app includes `allow_sharing` and `expires_at`.

### Share page

`GET /s/{id}` in `app/web/share.py`, evaluated in this precedence order:

1. `allow_sharing == false` → render new `share_unavailable.html`
   ("This content isn't available to share") with App Store / Play Store CTAs.
2. else `expires_at` is in the past → render new `share_expired.html`
   ("This post has expired — open the app for the latest") with App Store / Play
   Store CTAs.
3. else → existing `share.html`.

Both new templates reuse the brand styling and store-CTA markup already in
`share.html` / `share_not_found.html`.

Unchanged: delete, reaction, and view-count endpoints.

## Flutter UI

### Create Announcement screen (`create_broadcast.dart`)

Add two checkboxes below the caption field, matching the Figma layout, **both
unchecked by default**:

- ☐ `Do not allow sharing this video outside the app.`
- ☐ `Auto-delete video after 1 month.`

On submit, pass `allowSharing` and `expiresInDays` (30 when the auto-delete box
is checked, else `null`) to `postMessage`. The existing content-acknowledgement
checkbox remains the gate for the Post action.

### Service + model (`broadcast_service.dart`)

- `postMessage(...)` gains `bool allowSharing = true` and `int? expiresInDays`,
  sent in the request body as `allow_sharing` and `expires_in_days`.
- `BroadcastMessage` model parses `allow_sharing` and `expires_at`.

### Feed card + feed (`broadcast_message_card.dart`, `broadcast_feed.dart`)

- When `allow_sharing == false`: hide the Share button on the card and
  short-circuit `_shareMessage`.
- When `expires_at` is set: show an expiry note under the post — video:
  "The video will be automatically removed in 30 days."; other types:
  "This post will be automatically removed in 30 days." Visible to everyone.

### Localization

Add ARB entries (en + hi) for the two checkbox labels and the expiry note, per
`CLAUDE.md`. Run `flutter gen-l10n`.

## Edge Cases

- **Legacy posts**: missing fields → sharing allowed, never expires.
- **Both disabled and expired**: shows "not available" (share-disable takes
  precedence over expiry).
- **System/campaign cards**: default sharing-allowed, no expiry unless
  explicitly set.
- **Consistency**: the expiry filter applies to all feed read paths.

## Migration

None required. Defaults are applied at read time; no backfill needed. New fields
are optional.

## Testing

**Backend**
- `create_message` persists `allow_sharing` and computes `expires_at`.
- Feed excludes expired posts (and includes non-expired + legacy null).
- `/s/{id}` renders available / expired / unavailable for the three states.
- Legacy doc (no fields) behaves as allowed + non-expiring.

**Flutter**
- Widget test: two checkboxes default off; correct values sent on submit.
- Widget test: card hides Share when `allow_sharing == false`.
- Widget test: expiry note shown when `expires_at` is set.

**Regression**
- Existing broadcast feed + share page tests still pass.

## Out of Scope

- Editing expiry/share settings after posting.
- Countdown timers.
- Hard-deleting Mux assets at expiry.
- Custom expiry durations.
