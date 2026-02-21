# m360-backend

FastAPI wrapper over Quran Foundation APIs with JWT authentication, Masjid nearby search, and feature flags.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- MongoDB

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:

   Create a `.env` file in the root directory:

   **Quran API:**
   ```
   QURAN_CLIENT_ID=your_client_id
   QURAN_CLIENT_SECRET=your_client_secret
   QURAN_BASE_URL=your_base_url
   QURAN_OAUTH_URL=your_oauth_url
   ```

   **MongoDB:**
   ```
   MONGO_URI=mongodb://localhost:27017
   MONGO_DB_NAME=m360
   ```

   **JWT Authentication:**
   ```
   JWT_SECRET_KEY=your-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=60
   ```

   **Masjid nearby search (Google Places API):**
   ```
   GOOGLE_PLACES_API_KEY=your_google_places_api_key
   MASJID_SEARCH_RADIUS_KM=10
   MASJID_LOCATION_ENABLED=true
   ```

   When `GOOGLE_PLACES_API_KEY` is set, nearby masjids are fetched from **Google Places API (Nearby Search)**. Enable "Places API" in [Google Cloud Console](https://console.cloud.google.com/) for the project that owns the key (APIs & Services → Enable APIs → Places API). If the key is not set, the app falls back to MongoDB for masjid data.

   `MASJID_LOCATION_ENABLED` is a feature flag for pilot testing. Set to `true` to enable location-based masjid search; `false` to disable.

## API Overview

### Public
- `GET /health` - Health check

### Auth (no JWT required)
- `POST /auth/register` - Register user (username, password, optional email)
- `POST /auth/login` - Login (returns JWT)

### Protected (JWT required)
- `GET /chapters` - List chapters
- `GET /chapters/{chapter_id}` - Chapter by ID
- `GET /verses/by-chapter/{chapter_id}` - Verses by chapter
- `GET /verses/by-juz/{juz_id}` - Verses by juz
- `GET /juzs` - List juzs
- `GET /juzs/{juz_id}` - Juz by ID
- `GET /audio/chapter?chapter_id=&recitation_id=` - Chapter audio
- `GET /audio/verse?verse_key=&recitation_id=` - Verse audio
- `GET /masjid/nearby?latitude=&longitude=` - Nearby masjids (feature-flagged)

## Feature Flags

The `feature_flag` module provides reusable feature flag support. Use `FeatureFlagProvider` interface and `EnvFeatureFlagProvider` implementation. Add keys in `feature_flag/feature_keys.py` and check with `feature_flag_provider.is_enabled(FeatureKeys.KEY)`.

## Starting the Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or with Python:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Health Check

```bash
curl http://localhost:8000/health
```
