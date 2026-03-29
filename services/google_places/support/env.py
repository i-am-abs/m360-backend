import os

from dotenv import load_dotenv

from constants.env_keys import EnvKeys
from constants.masjid_query import MasjidQueryLimits
from constants.paths import PROJECT_ROOT


def load_project_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def get_google_places_api_key() -> str:
    load_project_dotenv()
    api_key = os.getenv(EnvKeys.GOOGLE_PLACES_API_KEY, "").strip()
    if not api_key:
        raise ValueError(
            "Missing GOOGLE_PLACES_API_KEY. Set it in .env to use Masjid search."
        )
    return api_key


def is_masjid_module_enabled() -> bool:
    load_project_dotenv()
    return bool(os.getenv(EnvKeys.GOOGLE_PLACES_API_KEY, "").strip())


def get_masjid_search_default_radius_meters() -> int:
    load_project_dotenv()
    raw = os.getenv(
        EnvKeys.MASJID_SEARCH_RADIUS_METERS,
        str(MasjidQueryLimits.SEARCH_RADIUS_DEFAULT_FALLBACK_M),
    ).strip()
    try:
        v = int(raw)
    except ValueError:
        v = MasjidQueryLimits.SEARCH_RADIUS_DEFAULT_FALLBACK_M
    return max(
        MasjidQueryLimits.SEARCH_RADIUS_MIN_M,
        min(MasjidQueryLimits.SEARCH_RADIUS_MAX_M, v),
    )
