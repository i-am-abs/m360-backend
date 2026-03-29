import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_project_dotenv() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def get_google_places_api_key() -> str:
    load_project_dotenv()
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing GOOGLE_PLACES_API_KEY. Set it in .env to use Masjid search."
        )
    return api_key


def is_masjid_module_enabled() -> bool:
    load_project_dotenv()
    return bool(os.getenv("GOOGLE_PLACES_API_KEY", "").strip())


def get_masjid_search_default_radius_meters() -> int:
    load_project_dotenv()
    raw = os.getenv("MASJID_SEARCH_RADIUS_METERS", "5000").strip()
    try:
        v = int(raw)
    except ValueError:
        v = 5000
    return max(500, min(50000, v))
