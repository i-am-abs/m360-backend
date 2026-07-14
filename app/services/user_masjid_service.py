from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.core.enums.masjid import MasjidSaveLimit
from app.exceptions.base import ApiException
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import PlacesReader
from app.interfaces.user_repository import UserRepository
from app.repositories.user_store_helpers import resolve_canonical_phone
from app.utils.admin_link import resolve_committee_for_place
from app.utils.masjid import get_deterministic_masjid_metadata

_MASJID_SAVE_LIMIT_MESSAGE = (
    "You are not allowed to save more than 3 masjids at a time."
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
                resolved_id = place.get("id") or pid
                meta = get_deterministic_masjid_metadata(resolved_id)
                committee = resolve_committee_for_place(
                    resolved_id,
                    admin_store=self._admin_store,
                    masjid_store=self._masjid_store,
                )
                view = MasjidDetailsPresenter.to_view(
                    place,
                    has_donations=meta["hasDonationsEnabled"],
                    has_announcements=meta["hasAnnouncementsEnabled"],
                    donation_count=meta["donationUpdatesCount"],
                    announcement_count=meta["announcementUpdatesCount"],
                    is_added=True,
                    saved_count=len(place_ids),
                    committee_data=committee["details"] if committee["has_committee"] else None,
                )
                view["committee"] = committee
                view.pop("raw", None)
                masjids.append(view)
            except Exception:
                masjids.append({
                    "place_id": pid,
                    "id": pid,
                    "unavailable": True,
                    "hasDonationsEnabled": False,
                    "hasAnnouncementsEnabled": False,
                    "donationUpdatesCount": 0,
                    "announcementUpdatesCount": 0,
                    "committee": {"has_committee": False, "details": None},
                })
        return {"count": len(masjids), "masjids": masjids}

    def add_my_masjid(self, user: Dict[str, Any], place_id: str) -> Dict[str, Any]:
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
