from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from httpx import Client, ConnectError, HTTPStatusError, TimeoutException

from constants.system_config import SystemConfig
from logger.Logger import Logger

logger = Logger.get_logger(__name__)

_GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_in_india(address: str, api_key: str) -> Optional[Tuple[float, float]]:
    q = (address or "").strip()
    if not q:
        return None
    params = {
        "address": q,
        "components": "country:IN",
        "region": "in",
        "key": api_key,
    }
    url = f"{_GEOCODE_BASE}?{urlencode(params)}"
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

    status = data.get("status")
    if status != "OK":
        logger.debug("Geocoding status=%s for %r", status, q)
        return None
    results = data.get("results") or []
    if not results:
        return None
    loc = (results[0].get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return (float(lat), float(lng))
    except (TypeError, ValueError):
        return None
