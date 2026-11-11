# Muslim360 Backend (m360-backend)

FastAPI backend for the **Muslim360** mobile app — Quran content, masjid discovery, committee management, location-based feature modules, broadcasts, donations, and an admin panel.

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

- API base: `https://muslim360.in/api/v1`
- Swagger: `https://muslim360.in/docs`
- Admin UI: `https://muslim360.in/admin/login`

