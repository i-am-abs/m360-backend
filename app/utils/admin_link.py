from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.interfaces.admin_repository import AdminRepository
from app.interfaces.masjid_repository import MasjidRepository
from app.utils.phone import phone_lookup_variants


def resolve_committee_for_place(
        place_id: str,
        *,
        admin_store: Optional[AdminRepository] = None,
        masjid_store: Optional[MasjidRepository] = None,
) -> Dict[str, Any]:
    """Build committee payload from approved masjid admins, else stored committee doc."""
    if admin_store is not None:
        admins = admin_store.list_approved_for_place(place_id)
        if admins:
            primary = admins[0]
            return {
                "has_committee": True,
                "details": {
                    "adminId": primary.get("admin_id"),
                    "name": primary.get("name"),
                    "phone": primary.get("phone"),
                    "role": primary.get("role"),
                    "status": primary.get("status"),
                    "committeeId": primary.get("committee_id"),
                    "profileImage": primary.get("profile_image"),
                    "masjidPlaceId": primary.get("masjid_place_id"),
                },
            }

    if masjid_store is not None:
        stored = masjid_store.get_committee(place_id)
        if stored:
            nested = stored.get("committee")
            if nested:
                return {"has_committee": True, "details": nested}
            # timings/amenities-only docs are not a committee
            if any(stored.get(k) for k in ("name", "phone", "admin_id", "adminId")):
                return {"has_committee": True, "details": stored}

    return {"has_committee": False, "details": None}


def ensure_admin_user_link(
        admin_store: AdminRepository,
        *,
        user_id: str,
        phone: Optional[str],
) -> List[Dict[str, Any]]:
    """Link admin rows for this phone to user_id; return approved docs for the user."""
    if not user_id:
        return []

    linked = admin_store.list_by_user_id(user_id)
    if linked:
        return linked

    if not phone:
        return []

    matches = admin_store.list_by_phone(phone)
    for doc in matches:
        admin_id = doc.get("admin_id")
        if not admin_id:
            continue
        updates: Dict[str, Any] = {}
        if doc.get("user_id") != user_id:
            updates["user_id"] = user_id
        # Normalize legacy 10-digit phones when possible
        try:
            from app.utils.phone import canonicalize_india_phone
            canonical = canonicalize_india_phone(phone)
            if doc.get("phone") != canonical:
                updates["phone"] = canonical
        except ValueError:
            pass
        if updates:
            if "user_id" in updates and len(updates) == 1:
                admin_store.link_user(str(admin_id), user_id)
            else:
                admin_store.update_fields(str(admin_id), updates)
    return admin_store.list_by_user_id(user_id)


def phones_match(left: str, right: str) -> bool:
    left_variants = set(phone_lookup_variants(left))
    right_variants = set(phone_lookup_variants(right))
    return bool(left_variants & right_variants)
