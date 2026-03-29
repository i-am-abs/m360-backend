# m360-backend

FastAPI wrapper over [Quran Foundation Content API](https://api-docs.quran.foundation) with OAuth2 Client Credentials authentication.

## Prerequisites

- Python 3.11+
- pip

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Create a `.env` file in the project root.

   **Required (server-side only):**
   - `QURAN_CLIENT_ID` or `QF_CLIENT_ID` — from [Quran Foundation request access](https://api-docs.quran.foundation/request-access)
   - `QURAN_CLIENT_SECRET` or `QF_CLIENT_SECRET` — never expose client-side

   **Optional:**
   - `QF_ENV` — `production` or `prelive` (default). When set, API and OAuth base URLs are chosen automatically:
     - **production**: `https://apis.quran.foundation`, `https://oauth2.quran.foundation`
     - **prelive**: `https://apis-prelive.quran.foundation`, `https://prelive-oauth2.quran.foundation`
   - `QURAN_BASE_URL` / `QURAN_OAUTH_URL` — override base URLs (must not include `/content/api` in base URL; paths in code already do).
   - `APP_ENV` — for loading `.env.prod` / `.env.preprod` / `.env.dev` / `.env.local` if present.

   **Masjid / Google Places (optional):**
   - `GOOGLE_PLACES_API_KEY` — enables masjid search endpoints; must stay server-side only. Responses pass through Google’s JSON (including `photos` metadata as returned by Places).

   **Production (e.g. Render):**
   - Set `QF_ENV=production` so the correct production API and OAuth URLs are used.
   - Ensure `QURAN_CLIENT_ID` and `QURAN_CLIENT_SECRET` are set in the host’s environment (no secrets in repo).
   - Do **not** set `QURAN_BASE_URL` to a URL that ends with `/content/api` (e.g. use `https://apis.quran.foundation` or leave unset when using `QF_ENV=production`).

## Project layout (Places / masjids)

| Area | Path |
|------|------|
| HTTP routers (Quran, auth, masjids) | `api/quran_routes.py`, `api/auth_routes.py`, `api/masjid_routes.py` |
| FastAPI dependencies | `api/dependencies.py` |
| Masjid / Places service (interface + impl) | `services/google_places/` (`contracts.py`, `provider.py`, `support/`) |
| Static config (URLs, geo, env keys, app) | `constants/google_places_config.py`, `constants/geo.py`, `constants/env_keys.py`, `constants/app_settings.py`, … |
| Quran upstream client | `client/quran_api_client.py` |

## API Endpoints (exposed)

- `GET /health` — health check
- `POST /auth/token` — obtain OAuth2 access token (for debugging; the app gets tokens automatically)
- `GET /chapters?language=en` — all chapters
- `GET /verses/by-chapter/{chapter_id}` — verses by chapter
- `GET /verses/by-juz/{juz_id}` — verses by juz
- `GET /juzs?language=en` — all juzs
- `GET /juzs/{juz_id}?language=en` — same data as `GET /verses/by-juz/{juz_id}` (alias)
- `GET /audio/chapter?chapter_id=&recitation_id=` — chapter recitation audio
- `GET /audio/verse?recitation_id=&verse_key=...` — verse recitation audio
- `GET /masjids/nearby`, `GET /masjids/search`, `GET /search` (same as masjid search), `GET /masjids/by-city`, `GET /masjids/place?place_id=...`, `GET /masjids/status` — Google Places masjid search (requires `GOOGLE_PLACES_API_KEY`)
- Audio query params accept **snake_case** or **camelCase** (e.g. `recitation_id` or `recitationId`, `verse_key` or `verseKey`).

Authentication follows [Quran Foundation OAuth2](https://api-docs.quran.foundation/docs/oauth2_apis_versioned/oauth-2-token-exchange): tokens are requested with Client Credentials, cached, and re-requested ~30s before expiry. Each API request sends `x-auth-token` and `x-client-id`. On 401, the app clears the token and retries once.

## Running the service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- API: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- ReDoc: http://localhost:8000/redoc  

## Docker

Multi-stage build (`Dockerfile`): dependencies install in a **builder** stage, then **build-essential is purged**, the venv is **trimmed** (`__pycache__`, `.pyc`, and `pip` / `setuptools` / `wheel` removed — not needed to run the app). The final image is **slim** Python + venv only, typically **well under ~400 MB** vs ~1+ GB for a single-stage full Python image.

```bash
docker build -t m360-backend .
docker run -p 8000:8000 m360-backend
```

Pass secrets at runtime (do not bake `.env` into the image):

```bash
docker run -p 8000:8000 --env-file .env m360-backend
```
