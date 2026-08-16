from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from app.core.enums.masjid import MasjidSaveLimit
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import PlacesReader
from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import resolve_canonical_phone
from app.utils.admin_link import user_is_approved_masjid_admin
from app.utils.amenities import empty_amenity_status
from app.utils.masjid_view import build_masjid_detail_view

_MASJID_SAVE_LIMIT_MESSAGE = (
    "You are not allowed to save more than 3 masjids at a time."
)
_MASJID_ADMIN_CANNOT_ADD_MESSAGE = (
    "You already manage a masjid as an admin, so it cannot be added to My Masjid."
)


class UserMasjidService:
    def __init__(
            self,
            store: UserRepository,
            places_reader: PlacesReader,
            masjid_store: Optional[MasjidRepository] = None,
            admin_store: Optional[AdminRepository] = None,
    ) -> None:
        self._store = store
        self._places_reader = places_reader
        self._masjid_store = masjid_store
        self._admin_store = admin_store

    @staticmethod
    def _phone_number(user: Dict[str, Any]) -> str:
        return resolve_canonical_phone(str(user["phone_number"]))

    def list_my_masjids(self, user: Dict[str, Any]) -> Dict[str, Any]:
        phone_number = self._phone_number(user)
        place_ids = self._store.list_favorites(phone_number)
        masjids: List[Dict[str, Any]] = []
        for pid in place_ids:
            try:
                place = self._places_reader.get_place_by_id(pid)
                if not isinstance(place, dict):
                    raise ValueError("invalid place")
                view = build_masjid_detail_view(
                    place,
                    place_id=pid,
                    is_added=True,
                    saved_count=len(place_ids),
                    admin_store=self._admin_store,
                    masjid_store=self._masjid_store,
                    current_user=user,
                    include_raw=False,
                )
                masjids.append(view)
            except Exception:
                masjids.append({
                    "place_id": pid,
                    "id": pid,
                    "unavailable": True,
                    "hasDonationsEnabled": False,
                    "hasAnnouncementsEnabled": True,
                    "donationUpdatesCount": 0,
                    "announcementUpdatesCount": 0,
                    "timings": [],
                    "prayerTimings": [],
                    "amenities": [],
                    "amenityStatus": empty_amenity_status(),
                    "onboardingDone": False,
                    "isAdmin": False,
                    "isCurrentUserAdmin": False,
                    "adminStatus": {"label": "unverified", "message": ""},
                    "committee": {
                        "hasCommittee": False,
                        "has_committee": False,
                        "details": [],
                    },
                })
        return {"count": len(masjids), "masjids": masjids}

    def add_my_masjid(self, user: Dict[str, Any], place_id: str) -> Dict[str, Any]:
        if user_is_approved_masjid_admin(
                current_user=user,
                admin_store=self._admin_store,
        ):
            raise ApiException(
                _MASJID_ADMIN_CANNOT_ADD_MESSAGE,
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        phone_number = self._phone_number(user)
        favorites = self._store.list_favorites(phone_number)
        if (
                place_id not in favorites
                and len(favorites) >= MasjidSaveLimit.MAX_FAVORITES.value
        ):
            raise ApiException(
                _MASJID_SAVE_LIMIT_MESSAGE,
                status_code=HTTPStatus.BAD_REQUEST.value,
            )
        favorites = self._store.add_favorite(phone_number, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}

    def remove_my_masjid(self, user: Dict[str, Any], place_id: str) -> Dict[str, Any]:
        phone_number = self._phone_number(user)
        favorites = self._store.remove_favorite(phone_number, place_id)
        return {"place_id": place_id, "favorite_place_ids": favorites}
