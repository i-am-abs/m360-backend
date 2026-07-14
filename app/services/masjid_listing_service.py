from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_listing_repository import MasjidListingRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.utils.admin_link import ensure_admin_user_link, resolve_committee_for_place
from app.utils.masjid import get_deterministic_masjid_metadata
from app.utils.structured_log import log_event, log_timing


class MasjidListingService:
    def __init__(
            self,
            admin_store: AdminRepository,
            listing_store: MasjidListingRepository,
            search_service: MasjidSearchService,
            user_store: UserRepository,
            masjid_store: Optional[MasjidRepository] = None,
    ) -> None:
        self._admin_store = admin_store
        self._listing_store = listing_store
        self._search_service = search_service
        self._user_store = user_store
        self._masjid_store = masjid_store

    def list_masjids_for_user(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        user_id = str(user.get("user_id") or "")
        phone = str(user.get("phone_number") or "")

        with log_timing("masjid_listing", "list", user_id=user_id):
            admin_docs = ensure_admin_user_link(
                self._admin_store,
                user_id=user_id,
                phone=phone or None,
            )
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

            items: List[Dict[str, Any]] = []
            for place_id in place_ids:
                listing = listings.get(place_id, {})
                admin_status = listing.get("admin_status") or {
                    "label": "unverified",
                    "message": listing.get("message") or "",
                }
                items.append(self._build_item(
                    place_id=place_id,
                    admin_status=admin_status,
                    favorite_ids=favorite_ids,
                    saved_count=len(favorite_ids),
                ))

        log_event("masjid_listing", "listed", user_id=user_id, count=len(items))
        return items

    def _build_item(
            self,
            *,
            place_id: str,
            admin_status: Dict[str, Any],
            favorite_ids: List[str],
            saved_count: int,
    ) -> Dict[str, Any]:
        try:
            place = self._search_service.get_place_by_id(place_id)
        except Exception:
            place = {"id": place_id, "unavailable": True}

        pid = place.get("id") or place_id
        meta = get_deterministic_masjid_metadata(pid)
        committee = resolve_committee_for_place(
            pid,
            admin_store=self._admin_store,
            masjid_store=self._masjid_store,
        )
        view = MasjidDetailsPresenter.to_view(
            place,
            has_donations=meta["hasDonationsEnabled"],
            has_announcements=meta["hasAnnouncementsEnabled"],
            donation_count=meta["donationUpdatesCount"],
            announcement_count=meta["announcementUpdatesCount"],
            is_added=pid in favorite_ids,
            saved_count=saved_count,
            committee_data=committee["details"] if committee["has_committee"] else None,
        )
        # Presenter sets committee.has_committee from details is not None —
        # force the resolved shape for consistency.
        view["committee"] = committee
        view["id"] = pid
        view["name"] = view.get("name") or pid
        view["adminStatus"] = {
            "label": admin_status.get("label", "unverified"),
            "message": admin_status.get("message", ""),
        }
        # Drop bulky raw Google payload from list endpoint
        view.pop("raw", None)
        return view
