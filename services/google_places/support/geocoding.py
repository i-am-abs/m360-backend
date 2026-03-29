from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from constants.google_places_config import GooglePlacesConfig, GooglePlacesPayload
from constants.system_config import SystemConfig
from logger.Logger import Logger

logger = Logger.get_logger(__name__)


def geocode_in_india(address: str, api_key: str) -> Optional[Tuple[float, float]]:
    q = (address or "").strip()
    if not q:
        return None
    params = {
        "address": q,
        "components": GooglePlacesPayload.GEOCODE_COUNTRY_COMPONENTS,
        "region": GooglePlacesPayload.GEOCODE_REGION_BIAS,
        "key": api_key,
    }
    url = f"{GooglePlacesConfig.GEOCODE_JSON_URL.value}?{urlencode(params)}"
    try:
        with Client(timeout=SystemConfig.REQUEST_TIMEOUT.value) as client:
            response = client.get(url)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
    except (ConnectError, TimeoutException) as e:
        logger.warning("Geocoding unreachable: %s", e)
        return None
    except HTTPStatusError as e:
        logger.warning("Geocoding HTTP error: %s", e)
        return None

    if data.get("status") != "OK":
        logger.debug("Geocoding status=%s for %r", data.get("status"), q)
        return None
    results = data.get("results") or []
    if not results:
        return None
    loc = (results[0].get("geometry") or {}).get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return (float(lat), float(lng))
    except (TypeError, ValueError):
        return None
