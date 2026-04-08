from typing import Any, Dict, List

from services.google_places.contracts import MasjidPlacesService
from services.user_store import UserStore


class UserMasjidService:
    def __init__(self, store: UserStore, masjid_places_service: MasjidPlacesService):
        self._store = store
        self._masjid_places_service = masjid_places_service

    def list_my_masjids(self, user_id: str) -> Dict[str, Any]:
        favorite_place_ids = self._store.list_favorites(user_id)
        masjids: List[Dict[str, Any]] = []
        for place_id in favorite_place_ids:
            try:
                masjids.append(self._masjid_places_service.get_place_by_id(place_id))
            except Exception:
                masjids.append({"id": place_id, "unavailable": True})
        return {"count": len(masjids), "masjids": masjids}

    def add_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.add_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}

    def remove_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.remove_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}
