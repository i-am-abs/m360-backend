from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.api.v1.presenters.masjid_presenter import MasjidDetailsPresenter
from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.utils.admin_link import (
    committee_member_from_admin,
    is_user_admin_for_place,
    resolve_committee_for_place,
)
from app.utils.masjid import get_deterministic_masjid_metadata


def resolve_admin_status_for_place(
        place_id: str,
        *,
        admin_store: Optional[AdminRepository] = None,
        listing_admin_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Derive adminStatus from approved/pending admins; fall back to listing store."""
    if admin_store is not None:
        approved = admin_store.list_approved_for_place(place_id)
        if approved:
            return {
                "label": "verified",
                "message": listing_admin_status.get("message", "") if listing_admin_status else "",
            }
        pending = admin_store.list_for_place(place_id, status="pending")
        if pending:
            return {
                "label": "pending",
                "message": listing_admin_status.get("message", "") if listing_admin_status else "",
            }

    if listing_admin_status and listing_admin_status.get("label"):
        return {
            "label": str(listing_admin_status.get("label")),
            "message": str(listing_admin_status.get("message") or ""),
        }
    return {"label": "unverified", "message": ""}


def build_masjid_detail_view(
        place: Dict[str, Any],
        *,
        place_id: str,
        is_added: bool = False,
        saved_count: int = 0,
        admin_store: Optional[AdminRepository] = None,
        masjid_store: Optional[MasjidRepository] = None,
        listing_admin_status: Optional[Dict[str, Any]] = None,
        current_user: Optional[Dict[str, Any]] = None,
        include_raw: bool = False,
) -> Dict[str, Any]:
    """Full masjid payload used by details + admin listing endpoints."""
    pid = place.get("id") or place_id
    meta = get_deterministic_masjid_metadata(pid)
    announcement_count = int(meta["announcementUpdatesCount"])
    committee = resolve_committee_for_place(
        pid,
        admin_store=admin_store,
        masjid_store=masjid_store,
    )
    # Announcements are only enabled when the masjid has at least one committee member.
    has_announcements = bool(committee.get("hasCommittee"))
    prayer_timings: List[Dict[str, Any]] = []
    amenities: List[str] = []
    if masjid_store is not None:
        prayer_timings = masjid_store.get_timings(pid) or []
        amenities = masjid_store.get_amenities(pid) or []

    is_admin = is_user_admin_for_place(
        pid,
        current_user=current_user,
        admin_store=admin_store,
    )

    view = MasjidDetailsPresenter.to_view(
        place,
        has_donations=meta["hasDonationsEnabled"],
        has_announcements=has_announcements,
        donation_count=meta["donationUpdatesCount"],
        announcement_count=announcement_count,
        is_added=is_added,
        saved_count=saved_count,
        committee_data=committee["details"] if committee.get("hasCommittee") else [],
        prayer_timings=prayer_timings,
        amenities=amenities,
    )
    # Final payload reflects committee-driven announcements enablement.
    view["hasAnnouncementsEnabled"] = has_announcements
    view["committee_details"] = committee["details"] if committee.get("hasCommittee") else []
    view["committee"] = committee
    view["id"] = pid
    view["name"] = view.get("name") or pid
    view["adminStatus"] = resolve_admin_status_for_place(
        pid,
        admin_store=admin_store,
        listing_admin_status=listing_admin_status,
    )
    view["onboardingDone"] = len(prayer_timings) > 0
    view["isAdmin"] = is_admin
    view["isCurrentUserAdmin"] = is_admin

    approved_admins: List[Dict[str, Any]] = []
    pending_admins: List[Dict[str, Any]] = []
    if admin_store is not None:
        for doc in admin_store.list_for_place(pid, status="approved"):
            approved_admins.append(committee_member_from_admin(doc))
        for doc in admin_store.list_for_place(pid, status="pending"):
            pending_admins.append(committee_member_from_admin(doc))
    view["approvedAdmins"] = approved_admins
    view["pendingAdmins"] = pending_admins

    if not include_raw:
        view.pop("raw", None)
    return view
