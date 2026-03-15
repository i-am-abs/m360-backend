import os
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from httpx import Client, HTTPStatusError, TimeoutException

from constants.system_config import SystemConfig
from feature_flags.city_resolver import CityResolver

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _get_api_key() -> str:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    key = (
        os.getenv("GOOGLE_PLACES_API_KEY")
        or os.getenv("GOOGLE_GEOCODING_API_KEY")
        or os.getenv("GOOGLE_MAPS_API_KEY")
    )
    return (key or "").strip()


def _extract_city_from_components(components: List[Any]) -> Optional[str]:
    for comp in components:
        types = comp.get("types") or []
        if "locality" in types:
            return comp.get("long_name") or comp.get("short_name")
        if "administrative_area_level_2" in types and "political" in types:
            return comp.get("long_name") or comp.get("short_name")
    for comp in components:
        types = comp.get("types") or []
        if "postal_town" in types:
            return comp.get("long_name") or comp.get("short_name")
    return None


class GoogleCityResolver(CityResolver):
    def get_city(self, latitude: float, longitude: float) -> Optional[str]:
        api_key = _get_api_key()
        if not api_key:
            return None
        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                resp = client.get(
                    SystemConfig.GOOGLE_GEOCODE_URL.value,
                    params={"latlng": f"{latitude},{longitude}", "key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except (HTTPStatusError, TimeoutException):
            return None
        results = data.get("results") or []
        for r in results:
            city = _extract_city_from_components(r.get("address_components") or [])
            if city:
                return city
        return None
