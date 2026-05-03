from config.application_settings import MasjidModuleSettings
from services.google_places.contracts import MasjidPlacesService
from services.google_places.google_masjid_places_service import (
    GoogleMasjidPlacesService,
)


def create_masjid_places_service(
        settings: MasjidModuleSettings,
) -> MasjidPlacesService:
    key = settings.google_places_api_key or ""
    return GoogleMasjidPlacesService(api_key=key)
