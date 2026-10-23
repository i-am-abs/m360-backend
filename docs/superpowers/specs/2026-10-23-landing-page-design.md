# muslim360.in Landing Page — Design

Date: 2026-10-23
Status: Approved for planning
Repo: `m360-backend`

## Goal

Serve an app-marketing landing page at `muslim360.in/` with a hero, store buttons,
feature highlights, screenshots, and an FAQ — matching the app's brand.

## Routing

- New `GET /` → `landing.html`, served by the FastAPI backend (always registered;
  independent of the admin panel).
- Remove the current `/` → `/admin/login` redirect; admins use `/admin/login` directly.
- Unchanged: `/admin/*`, `/s/{id}`, `/embed/{id}`, `/.well-known/*`.
- Store URLs come from `settings.play_store_url` / `app_store_url`; logo from
  `/share-static/logo.png`.

## Page Structure

1. Sticky header: logo + "Muslim 360", nav anchors (Features, Screenshots, FAQ), store buttons.
2. Hero: headline, subcopy, Play/App Store buttons, brand-gradient phone mockup.
3. Features: 4 cards (prayer times & azaan, Quran reading + audio, masjid finder,
   masjid announcements).
4. Screenshots: 3 phone frames using brand-styled placeholders (replaceable later with
   images under `app/web/static/landing/`).
5. FAQ: 4 items.
6. Minimal footer: © Muslim 360 + privacy/terms links (only if URLs are configured).

## Brand / Visual

- Plus Jakarta Sans; green gradient `#61D47D → #ADFF8D`; ink `#091914`;
  muted `#5D6C67`; soft rounded cards; mobile-first responsive; max-width container.

## Non-Goals

- No CMS, analytics, or separate frontend project.
- No changes to share/deep-link/app-links behavior.

## Testing

- Render smoke test: `GET /` returns 200 and contains the headline, both store links,
  Features/Screenshots/FAQ markers.
- Existing share/embed tests stay green.
