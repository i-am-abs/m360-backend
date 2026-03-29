from typing import Optional

from services.google_places.contracts import (
    GoogleMasjidPlacesService,
    MasjidPlacesService,
)

_impl: Optional[GoogleMasjidPlacesService] = None


def get_masjid_places_service() -> MasjidPlacesService:
    global _impl
    if _impl is None:
        _impl = GoogleMasjidPlacesService()
    return _impl
