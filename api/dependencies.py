from typing import Optional

from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import create_config
from services.google_places.contracts import MasjidPlacesService
from services.google_places.provider import (
    get_masjid_places_service as _masjid_singleton,
)

_quran_client: Optional[QuranApiClient] = None


def get_quran_api_client() -> QuranApiClient:
    global _quran_client
    if _quran_client is None:
        _quran_client = QuranApiClient(create_config())
    return _quran_client


def get_masjid_places_service() -> MasjidPlacesService:
    return _masjid_singleton()
