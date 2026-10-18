from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.enums.admin_status import AdminRegistrationStatus
from app.core.enums.role import UserRole
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_listing_repository import MasjidListingRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.interfaces.masjid_service import MasjidSearchService
from app.interfaces.user_repository import UserRepository
from app.services.rbac_service import RbacService
from app.utils.admin_link import ensure_admin_user_link
from app.utils.masjid_view import build_masjid_detail_view
from app.utils.structured_log import log_event, log_timing

_LISTED_STATUSES = frozenset({
    AdminRegistrationStatus.PENDING.value,
    AdminRegistrationStatus.APPROVED.value,
})


class MasjidListingService:
    def __init__(
            self,
            admin_store: AdminRepository,
            listing_store: MasjidListingRepository,
            search_service: MasjidSearchService,
            user_store: UserRepository,
            masjid_store: Optional[MasjidRepository] = None,
            rbac: Optional[RbacService] = None,
    ) -> None:
        self._admin_store = admin_store
        self._listing_store = listing_store
        self._search_service = search_service
        self._user_store = user_store
        self._masjid_store = masjid_store
        self._rbac = rbac

    def list_masjids_for_user(
            self,
            user: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """List masjids for the user, plus a rejection message if any request was rejected.

        Super admins see every masjid that has a pending or approved admin.
        Regular admins see only masjids where their request is pending or approved.
        """
        user_id = str(user.get("user_id") or "")
        phone = str(user.get("phone_number") or "")

        with log_timing("masjid_listing", "list", user_id=user_id):
            linked_docs = ensure_admin_user_link(
                self._admin_store,
                user_id=user_id,
                phone=phone or None,
            )
            admin_docs = [
                doc for doc in linked_docs
                if doc.get("status") in _LISTED_STATUSES
            ]
            rejection_message = self._rejection_message(linked_docs, admin_docs)
            favorite_ids = self._user_store.list_favorites(phone) if phone else []

            role = (
                self._rbac.resolve_user_role(user)
                if self._rbac is not None
                else UserRole.USER.value
            )
            if role == UserRole.SUPER_ADMIN.value:
                place_ids = self._place_ids_with_any_admin()
            else:
                place_ids = {
                    str(doc["masjid_place_id"])
                    for doc in admin_docs
                    if doc.get("masjid_place_id")
                }

            listings = {
                doc["place_id"]: doc
                for doc in self._listing_store.list_by_place_ids(list(place_ids))
            }

            items: List[Dict[str, Any]] = []
            for place_id in place_ids:
                listing = listings.get(place_id, {})
                listing_status = listing.get("admin_status")
                items.append(self._build_item(
                    place_id=place_id,
                    listing_admin_status=listing_status,
                    favorite_ids=favorite_ids,
                    saved_count=len(favorite_ids),
                    current_user=user,
                ))

        log_event(
            "masjid_listing",
            "listed",
            user_id=user_id,
            role=role,
            count=len(items),
            rejected=rejection_message is not None,
        )
        return items, rejection_message

    @staticmethod
    def _rejection_message(
            linked_docs: List[Dict[str, Any]],
            listed_docs: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Latest rejection for a masjid the user has no other live request for."""
        live_places = {str(doc.get("masjid_place_id")) for doc in listed_docs}
        rejected = [
            doc for doc in linked_docs
            if doc.get("status") == AdminRegistrationStatus.REJECTED.value
               and str(doc.get("masjid_place_id")) not in live_places
        ]
        if not rejected:
            return None
        latest = max(rejected, key=lambda d: str(d.get("updated_at") or ""))
        reason = (latest.get("status_message") or "").strip()
        if reason:
            return f"Your admin request has been rejected. Reason: {reason}"
        return "Your admin request has been rejected."

    def _place_ids_with_any_admin(self) -> Set[str]:
        place_ids: Set[str] = set()
        for doc in self._admin_store.list_all():
            pid = doc.get("masjid_place_id")
            if pid and doc.get("status") in _LISTED_STATUSES:
                place_ids.add(str(pid))
        return place_ids

    def _build_item(
            self,
            *,
            place_id: str,
            listing_admin_status: Optional[Dict[str, Any]],
            favorite_ids: List[str],
            saved_count: int,
            current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            place = self._search_service.get_place_by_id(place_id)
        except Exception:
            place = {"id": place_id, "unavailable": True}

        return build_masjid_detail_view(
            place,
            place_id=place_id,
            is_added=place_id in favorite_ids or (place.get("id") in favorite_ids),
            saved_count=saved_count,
            admin_store=self._admin_store,
            masjid_store=self._masjid_store,
            listing_admin_status=listing_admin_status,
            current_user=current_user,
            include_raw=False,
        )
