# Muslim360 Backend (m360-backend)

FastAPI backend for the **Muslim360** mobile app — Quran content, masjid discovery, committee management, location-based feature modules, broadcasts, donations, and an admin panel.

---

## Table of contents

- [What this service does](#what-this-service-does)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running the API](#running-the-api)
- [Docker](#docker)
- [Authentication](#authentication)
- [API overview](#api-overview)
- [Location-based feature flags](#location-based-feature-flags)
- [Data stores](#data-stores)
- [External integrations](#external-integrations)
- [Admin panel](#admin-panel)
- [Scripts](#scripts)
- [Response & error format](#response--error-format)
- [Docs](#docs)

---

## What this service does

| Domain | Capability |
|--------|------------|
| **Quran** | Proxy to Quran Foundation APIs (chapters, verses, juz, audio) with OAuth2 |
| **Masjid discovery** | Nearby / search / by-city / place details via Google Places |
| **Masjid management** | Timings, amenities, announcements, committee, claims |
| **Feature flags** | Enable modules (e.g. masjid) only in launched cities by lat/lng |
| **Auth** | Phone OTP (MSG91) → bearer sessions for mobile users |
| **Broadcasts** | Follow masjids, feed, reactions, FCM push, WebSocket |
| **Donations** | Campaigns + Razorpay-oriented payment flow |
| **Uploads** | Images → Cloudflare R2; video → Mux |
| **Admin** | HTML panel (`/admin`) + JSON admin API (`/api/v1/admin`) |

Many integrations are **optional**. If MongoDB, Redis, R2, Mux, or FCM are not configured, the app still starts and those features degrade to stubs / NoOps.

---

## Tech stack

| Piece | Choice |
|-------|--------|
| Runtime | Python **3.12** |
| Framework | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| Database | MongoDB (pymongo, sync) |
| Cache / rate limit | Redis (optional) |
| Push | Firebase Admin / FCM |
| Object storage | Cloudflare R2 (S3 API via boto3) |
| Video | Mux |
| OTP | MSG91 |
| Places | Google Places |
| Quran | Quran Foundation OAuth + Content APIs |

See [`requirements.txt`](requirements.txt) for package pins.

---

## Repository layout

```
m360-backend/
├── main.py                 # ASGI entry: create_app()
├── Dockerfile
├── docker-compose.yml      # mongo + backend
├── requirements.txt
├── .env                    # local secrets (gitignored — create your own)
├── data/                   # JSON user-store fallback when Mongo/Redis off
├── scripts/                # seed & ops scripts
├── firebase/android/       # Android Firebase client config notes
└── app/
    ├── factory.py          # FastAPI app, middleware, routers, lifespan
    ├── bootstrap.py        # Wires stores & services onto app.state
    ├── api/
    │   ├── deps.py         # FastAPI Depends accessors
    │   └── v1/
    │       ├── router.py   # Registers all v1 endpoint routers
    │       ├── endpoints/  # HTTP handlers
    │       └── presenters/ # Response shaping (e.g. masjid details)
    ├── core/               # config, logging, enums
    ├── services/           # Business logic
    ├── repositories/       # Mongo / Redis / R2 / Mux / Places / FCM
    ├── interfaces/         # Abstract repository contracts
    ├── schemas/            # Pydantic request/response models
    ├── gateways/           # HTTP, MSG91, OAuth, Redis caching client
    ├── middleware/         # Path normalize, request context, rate limit
    ├── exceptions/         # ApiException + handlers
    ├── utils/              # geo, phone, response helpers, region matching
    └── web/                # Jinja admin UI (templates + static)
```

---

## Architecture

Request flow:

```
HTTP → middleware (path / request-id / CORS / rate-limit)
     → endpoint (app/api/v1/endpoints)
     → service (app/services)
     → repository / gateway (app/repositories, app/gateways)
     → MongoDB / Redis / external APIs
```

**Dependency injection** is manual:

1. `bootstrap(app, settings)` builds stores and services and attaches them to `app.state.*`
2. `app/api/deps.py` exposes `get_*` helpers that read from `request.app.state`
3. Endpoints declare `Depends(get_feature_flag_service)` (and similar)

Startup sequence:

1. `main.py` → `create_app()`
2. Load settings from `.env` (`app/core/config.py`)
3. Setup logging
4. `bootstrap()` — Redis / Mongo ping, wire services
5. Mount `/api/v1` and (if enabled) `/admin`
6. On shutdown, close Redis and Mongo clients

---

## Quick start

### Prerequisites

- Python 3.12+
- MongoDB (recommended for full features)
- Redis (optional, for cache + accurate multi-worker rate limits)
- A `.env` file in the project root

### Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Minimal `.env`

```env
APP_ENV=dev
APP_NAME=m360.quran.api
SERVER_PORT=8002
SECRET_KEY=change-me-in-production

MONGODB_ENABLED=true
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=m360

REDIS_ENABLED=false

# Phone OTP
MSG91_AUTH_KEY=
MSG91_WIDGET_ID=
MSG91_COUNTRY_CODE=91

# Quran Foundation
QURAN_CLIENT_ID=
QURAN_CLIENT_SECRET=

# Masjid search
GOOGLE_PLACES_API_KEY=

# Platform admin panel login: email:password[,email2:password2]
SUPER_ADMINS=admin@example.com:your-password

# Optional
FCM_ENABLED=false
FIREBASE_CREDENTIALS_FILE=
RATE_LIMIT_ENABLED=true
ADMIN_PANEL_ENABLED=true
INTERNAL_API_KEY=
```

Copy and fill remaining keys as you enable R2, Mux, Razorpay, etc. (see [Configuration](#configuration)).

### Run locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

- API base: `http://localhost:8002/api/v1`
- Swagger: `http://localhost:8002/docs`
- Admin UI: `http://localhost:8002/admin/login`

### Seed feature flags (launched cities)

```bash
MONGODB_URI=mongodb://localhost:27017 MONGODB_DATABASE=m360 \
  python scripts/seed_feature_flags.py
```

This upserts default + Delhi / Aligarh / Faridabad regions and removes obsolete duplicate location keys.

---

## Configuration

Settings live in `app/core/config.py` and are loaded from environment / `.env`.

### Core

| Variable | Default | Notes |
|----------|---------|-------|
| `APP_ENV` | `prod` | Environment label |
| `APP_NAME` | `m360.quran.api` | Logger / app name |
| `SERVER_PORT` | `8000` | Used by Docker CMD |
| `SECRET_KEY` | `change-me-in-production` | Admin JWT signing |
| `LOGGING_LEVEL` | `INFO` | |
| `UVICORN_WORKERS` | `2` | Docker |

### MongoDB / Redis

| Variable | Default | Notes |
|----------|---------|-------|
| `MONGODB_ENABLED` | `false` | Must be `true` + URI for full platform |
| `MONGODB_URI` | — | Connection string |
| `MONGODB_DATABASE` | `m360` | |
| `REDIS_ENABLED` | `false` | |
| `REDIS_URL` | — | e.g. `redis://localhost:6379/0` |
| `REDIS_KEY_PREFIX` | `m360` | |
| `API_GET_CACHE_TTL_SECONDS` | `300` | Quran cache + feature-flag catalog TTL |

### Auth & admin

| Variable | Default | Notes |
|----------|---------|-------|
| `AUTH_SESSION_TTL_SECONDS` | `0` | `0` = never expires |
| `AUTH_FORCE_INFINITE_SESSIONS` | `true` | |
| `SUPER_ADMINS` | — | `email:password,...` for admin panel |
| `ADMIN_PANEL_ENABLED` | `true` | Mount `/admin` |
| `ADMIN_SESSION_TTL_SECONDS` | `86400` | |
| `INTERNAL_API_KEY` | — | Header `X-Internal-Api-Key` |

### Integrations (set when needed)

| Area | Variables |
|------|-----------|
| MSG91 | `MSG91_AUTH_KEY`, `MSG91_WIDGET_ID`, `MSG91_COUNTRY_CODE` |
| Quran | `QURAN_CLIENT_ID`, `QURAN_CLIENT_SECRET`, `QURAN_BASE_URL`, `QURAN_OAUTH_URL` |
| Places | `GOOGLE_PLACES_API_KEY`, `MASJID_SEARCH_RADIUS_METERS` |
| FCM | `FCM_ENABLED`, `FIREBASE_CREDENTIALS_FILE` |
| R2 | `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_PUBLIC_BASE_URL` |
| Mux | `MUX_TOKEN_ID`, `MUX_TOKEN_SECRET`, `MUX_WEBHOOK_SECRET`, `MUX_ENV_KEY` |
| Razorpay | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` |
| Rate limit | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS_PER_MINUTE`, `RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` |

Derived flags (code properties): `mongodb_configured`, `redis_configured`, `quran_api_configured`, `masjid_module_enabled`, `r2_configured`, `mux_configured`, `fcm_configured`, `payment_configured`.

---

## Running the API

```bash
# Dev with reload
uvicorn main:app --reload --port 8002

# Production-style
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Health checks:

```bash
curl http://localhost:8002/api/v1/health
curl http://localhost:8002/api/v1/health/live
curl http://localhost:8002/api/v1/health/ready
```

---

## Docker

```bash
docker compose up --build
```

[`docker-compose.yml`](docker-compose.yml) starts:

| Service | Ports | Notes |
|---------|-------|-------|
| `mongo` | `27017` | MongoDB 7, volume `mongo_data` |
| `backend` | `8002 → 8000` | Builds `Dockerfile`, uses `.env`, sets `MONGODB_URI=mongodb://mongo:27017` |

Image: Python 3.12-slim, timezone `Asia/Kolkata`, non-root user `m360`.

---

## Authentication

The API uses **several auth mechanisms** — do not mix them up.

### 1. Mobile users (phone OTP)

1. `POST /api/v1/auth/phone/request-otp` (or `/auth/login`)
2. User enters OTP → `POST /api/v1/auth/phone/verify-otp`
3. Response includes a **bearer session token**
4. Client sends `Authorization: Bearer <token>`

Optional: MSG91 webhook `POST /api/v1/webhooks/msg91/otp-events` for async request IDs.  
Refresh: `POST /api/v1/auth/refresh`.

Sessions live in Mongo (`sessions`) or the JSON/Redis user store, depending on config.

### 2. Quran Foundation OAuth (server-side)

- `POST /api/v1/auth/token` — client credentials for Quran APIs  
- `GET /api/v1/auth/token/status`

Used by the Quran proxy, not by end-user login.

### 3. Platform admin (web + JSON)

- Credentials from `SUPER_ADMINS`
- **Web**: JWT cookie `admin_token` after `/admin/login`
- **JSON**: `POST /api/v1/admin/login` → Bearer JWT (same `SECRET_KEY`)

### 4. Internal services

Header: `X-Internal-Api-Key: <INTERNAL_API_KEY>`  
Used by `/api/v1/internal/...` routes.

### Roles

| Role | Meaning |
|------|---------|
| `user` | Normal app user |
| `admin` | Committee / masjid admin (approved registration) |
| `super_admin` / platform admin | Platform operators |

Committee designations include imam, khatib, muezzin, caretaker, trustee, secretary, treasurer, committee_member, admin.

---

## API overview

All mobile/API routes are under **`/api/v1`**. Interactive docs: `/docs`.

### Health

| Method | Path |
|--------|------|
| GET | `/health`, `/health/live`, `/health/ready` |

### Auth

| Method | Path |
|--------|------|
| POST | `/auth/token`, `/auth/token/status` |
| POST | `/auth/phone/request-otp`, `/auth/phone/retry-otp`, `/auth/phone/verify-otp` |
| POST | `/auth/login`, `/auth/refresh` |

### Feature flags

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/features` | All flags for a location |
| GET | `/features/{module}` | Single module enabled? (`masjid`, `timings`, …) |
| GET | `/masjids/tab` | Masjid-tab UX contract (region + guest/follower/admin) |

Location query params (all optional): `latitude`, `longitude`, `location_key`, `country`, `state`, `city`.  
Latitude and longitude must be supplied **together**.

### Masjid discovery & entity

| Method | Path |
|--------|------|
| GET | `/masjids/nearby`, `/masjids/search`, `/search`, `/masjids/by-city`, `/masjids/place`, `/masjids/status` |
| GET | `/masjids/{place_id}/details` |
| GET/POST/DELETE | `/users/me/masjids`, `/users/me/masjids/{place_id}` |
| GET | `/masjids/my-committee` |
| GET/PUT | `/masjids/{masjid_id}`, facilities, timings |
| POST | `/masjids/sync` |
| POST/DELETE | committee members |

> **Route order:** `/masjids/tab` is registered **before** `/masjids/{masjid_id}` so `tab` is not treated as an ID.

### Masjid content

| Method | Path |
|--------|------|
| GET | `/masjids` |
| POST/PUT | `/masjids/{place_id}/timings`, `/amenities` |
| PUT | `/masjids/{place_id}/announcements-enabled` |

### Admins & verification

| Method | Path |
|--------|------|
| POST | `/admins/register` |
| GET | `/admins` |
| PATCH | `/admins/{admin_id}/status` |
| GET | `/roles`, `/designations` |
| POST | `/verification-requests` |
| PATCH | `/verification-requests/{request_id}/status` |

### Broadcasts & FCM

| Method | Path |
|--------|------|
| POST | `/fcm/tokens` |
| POST/DELETE | `/masjids/{place_id}/follow` |
| GET/POST | `/masjids/{place_id}/broadcasts` |
| GET/POST | `/masjids/{masjid_id}/broadcast` (+ campaign-card, react, view, delete) |
| WS | `/api/v1/v1/ws/masjid/{masjid_id}` |

### Claims

| Method | Path |
|--------|------|
| POST/GET | `/masjids/{masjid_id}/claim`, `/claim/status` |
| GET/POST | `/admin/claims`, approve, reject, stats |

### Donations

| Method | Path |
|--------|------|
| POST/GET | `/masjids/{masjid_id}/campaigns` |
| GET/PUT/DELETE | `/campaigns/{campaign_id}` |
| POST | `/campaigns/{campaign_id}/donate` |
| GET | `/donations/{donation_id}/status`, `/donations/history`, donors |
| POST | `/webhooks/payment` |

### Uploads & webhooks

| Method | Path |
|--------|------|
| POST | `/uploads` |
| GET | `/upload/mux-url` |
| POST | `/webhook/mux` |
| POST | `/webhooks/msg91/otp-events` |

### Internal

| Method | Path | Auth |
|--------|------|------|
| GET | `/internal/masjids/{place_id}/timings` | `X-Internal-Api-Key` |
| POST | `/internal/masjids/{place_id}/broadcast` | `X-Internal-Api-Key` |

### Admin JSON API (`/api/v1/admin`)

Login, me, dashboard, users (block/unblock), masjids (list/import), donations.

---

## Location-based feature flags

Clients ask whether a **module** is on for the user's coordinates. Example: enable the **masjid** module only in Aligarh, Delhi, and Faridabad.

### Modules (`PlatformFeature`)

| Key | Aliases (path) | Notes |
|-----|----------------|-------|
| `masjid_discovery` | `masjid`, `masjids`, `masjid_module`, … | Launch-gated (never on for default `*`) |
| `timings` | `timing`, `prayer_timings` | |
| `verification` | `verify` | |
| `committee_registration` | `committee`, … | |

### Resolution order

1. Exact `location_key`
2. Coordinates inside a region shape (circle preferred; rectangle/`bounds` also supported)
3. Region name (`country` / `state` / `city`, with aliases)
4. Default document `location_key: "*"`

Overlapping regions: highest `priority`, then **smallest area**, then stable `location_key` tie-break. The catalog is cached in-process (`CachedFeatureFlagStore`) for `API_GET_CACHE_TTL_SECONDS`.

### Example curls

```bash
BASE=http://localhost:8002/api/v1

# Enabled (Aligarh)
curl -s "$BASE/features/masjid?latitude=27.8974&longitude=78.0880"

# Disabled (Mumbai)
curl -s "$BASE/features/masjid?latitude=19.0760&longitude=72.8777"

# All flags
curl -s "$BASE/features?latitude=28.6139&longitude=77.2090"

# Masjid tab UX
curl -s "$BASE/masjids/tab?latitude=27.8974&longitude=78.0880"
```

**Success (enabled):**

```json
{
  "status": "success",
  "message": "OK",
  "data": {
    "module": "masjid",
    "feature": "masjid_discovery",
    "enabled": true,
    "location": {
      "location_key": "IN-UP-Aligarh",
      "country": "IN",
      "state": "UP",
      "city": "Aligarh",
      "matched_by": "coordinates"
    }
  }
}
```

**Success (disabled):** same shape with `"enabled": false` and `"location_key": "*"`.

Seeded cities (see `scripts/seed_feature_flags.py`): **Delhi**, **Aligarh**, **Faridabad**, plus shapeless state fallback `IN-DL` and global `*`.

To launch a new city, upsert a document in `feature_flag_locations` with `center`, `radius_km`, and `features.masjid_discovery: true` (or extend the seed script).

---

## Data stores

### MongoDB (default DB `m360`)

| Collection | Purpose |
|------------|---------|
| `users`, `sessions`, `favorites` | Users, bearer sessions, favourite places |
| `masjids` | Masjid entities (2dsphere index) |
| `masjid_committees`, `masjid_listings` | Timings / amenities / listings |
| `admins`, `verification_requests`, `audit_logs` | Registration & audit |
| `feature_flag_locations` | Geo feature flags |
| `fcm_tokens`, `masjid_follows`, `masjid_followers` | Push & follow graph |
| `broadcasts`, `broadcast_messages`, `counters` | Broadcast feeds |
| `masjid_claims` | Claim workflow |
| `donation_campaigns`, `donations` | Donations |

### Redis (optional)

Quran/masjid response cache, alternate user store, rate limiting, MSG91 pending request-id buffer, internal timings cache.

### Fallbacks

- Without Mongo: many platform stores are NoOp; masjid platform features are limited.
- Without Redis: in-memory rate limit / MSG91 buffer (not multi-worker safe).
- `data/user_store.json` used when Mongo/Redis user stores are unavailable.

---

## External integrations

| Service | Role |
|---------|------|
| **Quran Foundation** | Content + OAuth |
| **Google Places** | Masjid search / details |
| **MSG91** | Phone OTP + webhook |
| **Firebase / FCM** | Device tokens & push |
| **Cloudflare R2** | Image uploads |
| **Mux** | Video direct upload + webhook |
| **Razorpay** | Donation payments + webhook |

Android Firebase notes live under [`firebase/android/`](firebase/android/).

---

## Admin panel

Enabled when `ADMIN_PANEL_ENABLED=true`.

| Path | Purpose |
|------|---------|
| `/admin/login` | Email/password (`SUPER_ADMINS`) |
| `/admin/dashboard` | Stats |
| `/admin/users`, `/admin/users/{id}` | Users, block/unblock |
| `/admin/masjids`, create/update/committee | Masjid ops |
| `/admin/claims` | Claims + pending admin registrations |
| `/admin/donations` | Donations page |
| `/admin/static/*` | Static assets |

Root `/` redirects to dashboard (if logged in) or login.

---

## Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/seed_feature_flags.py`](scripts/seed_feature_flags.py) | Upsert feature-flag regions; remove obsolete duplicates |
| [`scripts/fix_admin_links.py`](scripts/fix_admin_links.py) | Link `admins` ↔ `users` by phone; optional `--place-id`, `--approve` |

```bash
MONGODB_URI=... MONGODB_DATABASE=m360 python scripts/seed_feature_flags.py
MONGODB_URI=... python scripts/fix_admin_links.py [--place-id PLACE] [--approve]
```

---

## Response & error format

**Success**

```json
{
  "status": "success",
  "message": "OK",
  "data": { }
}
```

**Error**

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "..."
  }
}
```

Validation errors (`422`) may include an `error.fields` array. Rate limits return `429` / `RATE_LIMIT_EXCEEDED`.

---

## Docs

| URL | Description |
|-----|-------------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |

---

## License / notes

- Do **not** commit `.env`, Firebase private keys, or Mux/Razorpay secrets.
- Prefer Docker Compose secrets / env files over hard-coding credentials in `docker-compose.yml`.
- For production, set a strong `SECRET_KEY`, enable Mongo (+ Redis for multi-worker), and turn on only the integrations you need.
