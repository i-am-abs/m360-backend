from __future__ import annotations

from typing import Any, Dict, List, Set

from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_listing_repository import MasjidListingRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.schemas.masjid_content import AdminStatusView, MasjidListItem
from app.utils.structured_log import log_event, log_timing


class MasjidListingService:
    def __init__(
        self,
        admin_store: AdminRepository,
        listing_store: MasjidListingRepository,
        search_service: MasjidSearchService,
        user_store: UserRepository,
    ) -> None:
        self._admin_store = admin_store
        self._listing_store = listing_store
        self._search_service = search_service
        self._user_store = user_store

    def list_masjids_for_user(self, user: Dict[str, Any]) -> List[MasjidListItem]:
        user_id = str(user.get("user_id") or "")
        phone = str(user.get("phone_number") or "")

        with log_timing("masjid_listing", "list", user_id=user_id):
            admin_docs = self._admin_store.list_by_user_id(user_id)
            favorite_ids = self._user_store.list_favorites(phone) if phone else []

            place_ids: Set[str] = set(favorite_ids)
            for doc in admin_docs:
                pid = doc.get("masjid_place_id")
                if pid:
                    place_ids.add(str(pid))

            listings = {
                doc["place_id"]: doc
                for doc in self._listing_store.list_by_place_ids(list(place_ids))
            }

            items: List[MasjidListItem] = []
            for place_id in place_ids:
                name = self._resolve_name(place_id)
                listing = listings.get(place_id, {})
                admin_status = listing.get("admin_status") or {
                    "label": "unverified",
                    "message": listing.get("message") or "",
                }
                items.append(MasjidListItem(
                    id=place_id,
                    name=name,
                    admin_status=AdminStatusView(
                        label=admin_status.get("label", "unverified"),
                        message=admin_status.get("message", ""),
                    ),
                ))

        log_event("masjid_listing", "listed", user_id=user_id, count=len(items))
        return items

    def _resolve_name(self, place_id: str) -> str:
        try:
            place = self._search_service.get_place_by_id(place_id)
            return (
                place.get("displayName", {}).get("text")
                or place.get("name")
                or place_id
            )
        except Exception:
            return place_id
