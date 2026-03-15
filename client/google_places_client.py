import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from httpx import Client, HTTPStatusError, ConnectError, TimeoutException

from constants.system_config import SystemConfig
from exceptions.api_exception import ApiException
from logger.Logger import Logger

logger = Logger.get_logger(__name__)


def _load_env() -> None:
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path, override=False)


def _get_api_key() -> str:
    _load_env()
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing GOOGLE_PLACES_API_KEY. Set it in .env to use Masjid search."
        )
    return api_key


class GooglePlacesClient:
    def search_nearby_masjid(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1000,
        max_result_count: int = 10,
    ) -> List[Dict[str, Any]]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _get_api_key(),
            "X-Goog-FieldMask": SystemConfig.FIELD_MASK.value,
        }
        body = {
            "includedTypes": ["mosque"],
            "maxResultCount": max_result_count,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }

        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.post(
                    SystemConfig.GOOGLE_PLACES_SEARCH_NEARBY_URL.value,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                places = data.get("places") or []
                return self._normalize_places(places)
        except ConnectError as e:
            logger.error("Google Places API unreachable: %s", e)
            raise ApiException(
                "Cannot reach Google Places API. Check network.",
                status_code=503,
            ) from e
        except TimeoutException:
            raise ApiException("Google Places API timeout", status_code=504)
        except HTTPStatusError as e:
            logger.error("Google Places API error: %s", e.response.text)
            raise ApiException(
                f"Google Places API error: {e.response.status_code}",
                status_code=e.response.status_code,
            )

    def _normalize_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for p in places:
            name = (p.get("displayName") or {}).get("text") or ""
            address = p.get("formattedAddress") or ""
            loc = p.get("location") or {}
            result.append(
                {
                    "displayName": name,
                    "formattedAddress": address,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                    },
                }
            )
        return result

_places_client: Optional[GooglePlacesClient] = None


def get_places_client() -> GooglePlacesClient:
    global _places_client
    if _places_client is None:
        _places_client = GooglePlacesClient()
    return _places_client
