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


def is_masjid_module_enabled() -> bool:
    _load_env()
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    return bool(api_key)


def _max_photos_per_place() -> int:
    """
    Max Places Photo (media) API calls per place per request.
    Env MASJID_MAX_PHOTOS_PER_PLACE:
      - unset: use DEFAULT_MAX_PHOTOS_PER_PLACE (5)
      - 0: do not call Photo API (search-only; photos list empty)
      - 1..ABSOLUTE_MAX: cap photo fetches per place
    """
    _load_env()
    raw = os.getenv("MASJID_MAX_PHOTOS_PER_PLACE", "").strip()
    if not raw:
        return SystemConfig.DEFAULT_MAX_PHOTOS_PER_PLACE.value
    try:
        n = int(raw)
    except ValueError:
        return SystemConfig.DEFAULT_MAX_PHOTOS_PER_PLACE.value
    if n <= 0:
        return 0
    cap = SystemConfig.ABSOLUTE_MAX_PHOTOS_PER_PLACE.value
    return min(n, cap)


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
                return self._normalize_places(places, http_client=client)
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

    def search_masjid_by_name(
        self,
        query: str,
        max_result_count: int = 10,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _get_api_key(),
            "X-Goog-FieldMask": SystemConfig.FIELD_MASK.value,
        }
        body = {
            "textQuery": query,
            "includedType": "mosque",
            "maxResultCount": max_result_count,
        }

        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.post(
                    SystemConfig.GOOGLE_PLACES_SEARCH_TEXT_URL.value,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                places = data.get("places") or []
                return self._normalize_places(places, http_client=client)
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

    def search_masjid_by_city(
        self,
        city: str,
        max_result_count: int = 20,
    ) -> List[Dict[str, Any]]:
        if not city:
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _get_api_key(),
            "X-Goog-FieldMask": SystemConfig.FIELD_MASK.value,
        }
        body = {
            "textQuery": f"mosque in {city}",
            "includedType": "mosque",
            "maxResultCount": max_result_count,
        }

        try:
            with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
                response = client.post(
                    SystemConfig.GOOGLE_PLACES_SEARCH_TEXT_URL.value,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                places = data.get("places") or []
                return self._normalize_places(places, http_client=client)
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

    def _fetch_photo_uri(self, http_client: Client, photo_name: str) -> Optional[str]:
        if not (photo_name and isinstance(photo_name, str)):
            return None
        media_name = (
            f"{photo_name}/media" if not photo_name.endswith("/media") else photo_name
        )
        url = f"{SystemConfig.GOOGLE_PLACES_PHOTO_MEDIA_BASE.value}/{media_name}"
        params = {
            "key": _get_api_key(),
            "maxHeightPx": SystemConfig.PHOTO_MEDIA_MAX_HEIGHT_PX.value,
            "skipHttpRedirect": "true",
        }
        try:
            response = http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("photoUri")
        except (HTTPStatusError, Exception) as e:
            logger.warning("Could not resolve photo %s: %s", photo_name, e)
            return None

    def _normalize_places(
        self,
        places: List[Dict[str, Any]],
        http_client: Optional[Client] = None,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        max_photos = _max_photos_per_place()
        photo_media_calls = 0

        for p in places:
            name = (p.get("displayName") or {}).get("text") or ""
            address = p.get("formattedAddress") or ""
            loc = p.get("location") or {}
            photos: List[str] = []
            if http_client and max_photos > 0:
                photo_objs = (p.get("photos") or [])[:max_photos]
                for ph in photo_objs:
                    photo_name = ph.get("name") if isinstance(ph, dict) else None
                    if not photo_name:
                        continue
                    photo_media_calls += 1
                    uri = self._fetch_photo_uri(http_client, photo_name)
                    if uri:
                        photos.append(uri)
            result.append(
                {
                    "displayName": name,
                    "formattedAddress": address,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                    },
                    "photos": photos,
                }
            )

        if places:
            logger.info(
                "Masjid Google Places: 1 search request + %d photo media requests "
                "(%d places, max %d photos/place). Set MASJID_MAX_PHOTOS_PER_PLACE=0 "
                "to skip photo calls.",
                photo_media_calls,
                len(places),
                max_photos,
            )
        return result


_places_client: Optional[GooglePlacesClient] = None


def get_places_client() -> GooglePlacesClient:
    global _places_client
    if _places_client is None:
        _places_client = GooglePlacesClient()
    return _places_client
