from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List

from app.core.enums.masjid import MasjidSaveLimit
from app.exceptions.base import ApiException
from app.interfaces.masjid_service import PlacesReader
from app.interfaces.user_repository import UserRepository
from app.utils.masjid import get_deterministic_masjid_metadata


_MASJID_SAVE_LIMIT_MESSAGE = (
    "You are not allowed to save more than 3 masjids at a time."
)



class UserMasjidService:
    def __init__(self, store: UserRepository, places_reader: PlacesReader) -> None:
        self._store = store
        self._places_reader = places_reader

    def list_my_masjids(self, user_id: str) -> Dict[str, Any]:
        place_ids = self._store.list_favorites(user_id)
        masjids: List[Dict[str, Any]] = []
        for pid in place_ids:
            try:
                place = self._places_reader.get_place_by_id(pid)
                if isinstance(place, dict):
                    meta = get_deterministic_masjid_metadata(pid)
                    place.update(meta)
                masjids.append(place)
            except Exception:
                masjids.append({
                    "id": pid,
                    "unavailable": True,
                    "hasDonationsEnabled": False,
                    "hasAnnouncementsEnabled": False,
                    "donationUpdatesCount": 0,
                    "announcementUpdatesCount": 0,
                })
        return {"count": len(masjids), "masjids": masjids}

    def add_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.list_favorites(user_id)
        if (
            place_id not in favorites
            and len(favorites) >= MasjidSaveLimit.MAX_FAVORITES.value
        ):
            raise ApiException(
                _MASJID_SAVE_LIMIT_MESSAGE,
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        favorites = self._store.add_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}

    def remove_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.remove_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}
