from __future__ import annotations

from typing import Any, Dict, List

from app.core.logging import get_logger
from app.interfaces.masjid_service import PlacesReader
from app.interfaces.user_repository import UserRepository

_log = get_logger(__name__)


class UserMasjidService:
    def __init__(self, store: UserRepository, places_reader: PlacesReader) -> None:
        self._store = store
        self._places_reader = places_reader

    def list_my_masjids(self, user_id: str) -> Dict[str, Any]:
        place_ids = self._store.list_favorites(user_id)
        masjids: List[Dict[str, Any]] = []
        for pid in place_ids:
            try:
                masjids.append(self._places_reader.get_place_by_id(pid))
            except Exception:
                masjids.append({"id": pid, "unavailable": True})
        return {"count": len(masjids), "masjids": masjids}

    def add_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.add_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}

    def remove_my_masjid(self, user_id: str, place_id: str) -> Dict[str, Any]:
        favorites = self._store.remove_favorite(user_id, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}
