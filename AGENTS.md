# M360 Backend

Python 3.11+ FastAPI wrapper over [Quran Foundation Content API](https://apis.quran.foundation).

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

Or with Docker:

```bash
docker build -t m360-backend .
docker run -p 8002:8002 --env-file .env.prod m360-backend
```

## Config

Environment is loaded from `./.env` via pydantic-settings. `app/main.py` uses `APP_ENV` to load env-specific files (`.env.prod`, `.env.preprod`, `.env.dev`, `.env.local`).

`QF_ENV` controls which Quran Foundation API environment to use (production vs prelive).

Key vars (`app/core/config.py`):
- `QURAN_BASE_URL` — Quran API base
- `QURAN_CLIENT_ID` / `QURAN_CLIENT_SECRET` — OAuth2 credentials
- `JWT_EXPIRATION_MINUTES` — token lifetime (default 60)
- `MSG91_AUTH_KEY` — SMS OTP
- `GOOGLE_PLACES_API_KEY` — masjid search
- `MONGODB_URI` / `REDIS_URL` — optional persistent stores

## Endpoints (`app/api/v1/endpoints/`)

| Endpoint | File | Purpose |
|----------|------|---------|
| `/v1/quran/*` | `quran.py` | Proxy to Quran Foundation API |
| `/v1/auth/*` | `auth.py` | Phone OTP login |
| `/v1/masjid/*` | `masjid.py` | Google Places masjid search |
| `/v1/health` | `health.py` | Liveness check |
| `/v1/msg91-webhook` | `msg91_webhook.py` | SMS delivery callback |

## Architecture

`router.py` → endpoint (`auth.py`) → service (`app/services/`) → gateway (`app/gateways/`) or repository (`app/repositories/`).

- **Gateways** — external API clients (Quran Foundation, Google Places, MSG91). Use `httpx.AsyncClient`.
- **Repositories** — data access for MongoDB (optional, behind `mongodb_enabled` flag).
- **Redis** — optional response cache behind `redis_enabled` flag.

## Dependencies

- `fastapi` + `uvicorn` — web framework
- `pydantic-settings` — env config
- `httpx` — async HTTP
- `pymongo` — MongoDB
- `redis` + `hiredis` — Redis cache
- `pyjwt` — JWT tokens
- `python-dotenv` — .env bootstrap

## Notes

- No test directory detected. No CI/CD pipeline config.
- CORS is wide open (`*`) in config.
- SSL context is created via `create_ssl_context()` for secure outbound connections.
