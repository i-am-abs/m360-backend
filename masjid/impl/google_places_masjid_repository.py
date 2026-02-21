"""
Google Places API implementation of MasjidRepository.
Uses Places Nearby Search to find mosques/masjids near a location.
"""
from typing import Any, Dict, List

import httpx

from masjid.masjid_repository import MasjidRepository
from utils.logger import Logger

logger = Logger.get_logger(__name__)

NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
MAX_RADIUS_METERS = 50000  # Google Places limit
DEFAULT_KEYWORD = "mosque"


class GooglePlacesMasjidRepository(MasjidRepository):
    """Fetches nearby masjids using Google Places API (Nearby Search)."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Google Places API key is required")
        self._api_key = api_key

    def find_nearby(
        self,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        radius_m = min(int(radius_km * 1000), MAX_RADIUS_METERS)
        params = {
            "location": f"{latitude},{longitude}",
            "radius": radius_m,
            "keyword": DEFAULT_KEYWORD,
            "key": self._api_key,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(NEARBY_SEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error("Google Places API request failed: %s", e)
            return []

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning(
                "Google Places API status: %s - %s. Enable Places API (Nearby Search) and check key restrictions.",
                status,
                data.get("error_message", ""),
            )
            return []

        results = data.get("results", [])[:limit]
        return [self._map_place_to_masjid(p) for p in results]

    @staticmethod
    def _map_place_to_masjid(place: Dict[str, Any]) -> Dict[str, Any]:
        geo = place.get("geometry", {}).get("location", {})
        return {
            "id": place.get("place_id", ""),
            "place_id": place.get("place_id", ""),
            "name": place.get("name", ""),
            "address": place.get("vicinity", ""),
            "latitude": geo.get("lat"),
            "longitude": geo.get("lng"),
            "location": {
                "type": "Point",
                "coordinates": [geo.get("lng"), geo.get("lat")],
            },
        }
